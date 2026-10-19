// Offline test host for the DecentSampler AU (aumu/Dsmp/Dldy).
//
//   dshost dump-state
//       Prints the AU's default fullState (and the decoded JUCE XML) to stdout.
//   dshost render <state.xml> <score.txt> <out.wav> [settleSeconds]
//       Restores a JUCE state XML, waits for the preset to load, plays the score and writes a
//       44.1 kHz stereo float WAV. Score lines: "<onSec> <durSec> <note> <velocity>".
import AVFoundation
import AudioToolbox
import Foundation

let exsPath = ProcessInfo.processInfo.environment["DSHOST_EXS"]  // render an .exs through Apple's AUSampler
let useDLS = ProcessInfo.processInfo.environment["DSHOST_DLS"] != nil || exsPath != nil
let desc = AudioComponentDescription(componentType: kAudioUnitType_MusicDevice,
                                     componentSubType: exsPath != nil ? kAudioUnitSubType_Sampler
                                         : useDLS ? kAudioUnitSubType_DLSSynth : 0x4473_6d70, // 'Dsmp'
                                     componentManufacturer: useDLS ? kAudioUnitManufacturer_Apple : 0x446c_6479, // 'Dldy'
                                     componentFlags: 0, componentFlagsMask: 0)

func instantiate() -> AVAudioUnit {
    let sem = DispatchSemaphore(value: 0)
    var unit: AVAudioUnit?
    AVAudioUnit.instantiate(with: desc, options: []) { u, err in
        if let err { FileHandle.standardError.write("instantiate failed: \(err)\n".data(using: .utf8)!) }
        unit = u
        sem.signal()
    }
    sem.wait()
    guard let unit else { exit(2) }
    return unit
}

// JUCE wraps its XML state as: magic 0x21324356 (LE u32), size (LE u32), UTF-8 XML, NUL.
func decodeJuce(_ d: Data) -> String? {
    guard d.count > 8 else { return nil }
    let magic = d.prefix(4).withUnsafeBytes { $0.loadUnaligned(as: UInt32.self) }
    guard magic == 0x2132_4356 else { return String(data: d, encoding: .utf8) }
    let size = Int(d.subdata(in: 4..<8).withUnsafeBytes { $0.loadUnaligned(as: UInt32.self) })
    return String(data: d.subdata(in: 8..<min(d.count, 8 + size)), encoding: .utf8)?
        .trimmingCharacters(in: CharacterSet(charactersIn: "\0"))
}

func encodeJuce(_ xml: String) -> Data {
    var body = xml.data(using: .utf8)!
    body.append(0)
    var d = Data()
    var magic = UInt32(0x2132_4356).littleEndian
    var size = UInt32(body.count).littleEndian
    d.append(Data(bytes: &magic, count: 4))
    d.append(Data(bytes: &size, count: 4))
    d.append(body)
    return d
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    print("usage: dshost dump-state | render <state.xml> <score.txt> <out.wav> [settle]")
    exit(1)
}

if args[1] == "dump-state" {
    let u = instantiate()
    let state = u.auAudioUnit.fullState ?? [:]
    for (k, v) in state {
        if let d = v as? Data {
            print("key \(k): \(d.count) bytes")
            if let x = decodeJuce(d) { print(x) }
        } else {
            print("key \(k): \(v)")
        }
    }
    exit(0)
}

guard args[1] == "render", args.count >= 5 else { exit(1) }
let stateXML = try String(contentsOfFile: args[2], encoding: .utf8)
let score: [(Double, Double, UInt8, UInt8)] = try String(contentsOfFile: args[3], encoding: .utf8)
    .split(separator: "\n").compactMap { line in
        let f = line.split(separator: " ")
        guard f.count == 4, let a = Double(f[0]), let b = Double(f[1]),
              let n = UInt8(f[2]), let v = UInt8(f[3]) else { return nil }
        return (a, b, n, v)
    }
let settle = args.count > 5 ? Double(args[5])! : 4.0

let sr = 44100.0
let engine = AVAudioEngine()
let unit = instantiate()
engine.attach(unit)
let fmt = AVAudioFormat(standardFormatWithSampleRate: sr, channels: 2)!
engine.connect(unit, to: engine.mainMixerNode, format: fmt)
let block: AVAudioFrameCount = 256
try engine.enableManualRenderingMode(.offline, format: fmt, maximumFrameCount: block)

if !useDLS {
    var state = unit.auAudioUnit.fullState ?? [:]
    state["jucePluginState"] = encodeJuce(stateXML)
    unit.auAudioUnit.fullState = state
}
try engine.start()
if let exsPath {
    let url = URL(fileURLWithPath: exsPath) as CFURL
    var data = AUSamplerInstrumentData(fileURL: Unmanaged.passRetained(url),
                                       instrumentType: UInt8(kInstrumentType_EXS24), bankMSB: 0, bankLSB: 0, presetID: 0)
    let err = AudioUnitSetProperty(unit.audioUnit, kAUSamplerProperty_LoadInstrument, kAudioUnitScope_Global, 0,
                                   &data, UInt32(MemoryLayout<AUSamplerInstrumentData>.size))
    if err != noErr { FileHandle.standardError.write("EXS load failed: \(err)\n".data(using: .utf8)!); exit(3) }
}

let midi = unit.auAudioUnit.scheduleMIDIEventBlock!
let buf = AVAudioPCMBuffer(pcmFormat: engine.manualRenderingFormat, frameCapacity: block)!

// Let the preset load (the AU loads on a background thread) while rendering silence.
RunLoop.main.run(until: Date(timeIntervalSinceNow: settle))
if ProcessInfo.processInfo.environment["DSHOST_DEBUG"] != nil,
   let d = unit.auAudioUnit.fullState?["jucePluginState"] as? Data, let x = decodeJuce(d) {
    FileHandle.standardError.write("state after load:\n\(x.prefix(3000))\n".data(using: .utf8)!)
}
var t: AVAudioFramePosition = 0
func renderFrames(_ n: AVAudioFramePosition, into out: AVAudioFile?) throws {
    var left = n
    while left > 0 {
        let c = AVAudioFrameCount(min(AVAudioFramePosition(block), left))
        let st = try engine.renderOffline(c, to: buf)
        guard st == .success else { throw NSError(domain: "render", code: Int(st.rawValue)) }
        if let out { try out.write(from: buf) }
        left -= AVAudioFramePosition(c)
        t += AVAudioFramePosition(c)
    }
}
try renderFrames(AVAudioFramePosition(0.5 * sr), into: nil)

let outFile = try AVAudioFile(forWriting: URL(fileURLWithPath: args[4]),
                              settings: [AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: sr,
                                         AVNumberOfChannelsKey: 2, AVLinearPCMBitDepthKey: 32,
                                         AVLinearPCMIsFloatKey: true],
                              commonFormat: .pcmFormatFloat32, interleaved: false)
var events: [(Double, [UInt8])] = []
for (on, dur, n, v) in score {
    if dur == -2 {  // pitch bend: lsb n, msb v
        events.append((on, [0xE0, n, v]))
        continue
    }
    if dur < 0 {  // control change: number n, value v
        events.append((on, [0xB0, n, v]))
        continue
    }
    events.append((on, [0x90, n, v]))
    events.append((on + dur, [0x80, n, 0]))
}
events.sort { $0.0 < $1.0 }
let start = t
let end = (events.last?.0 ?? 0) + 3.0
var i = 0
while Double(t - start) / sr < end {
    let now = Double(t - start) / sr
    while i < events.count && events[i].0 <= now {
        // Real-time pacing so disk-streaming voices are fed like in a DAW.
        events[i].1.withUnsafeBufferPointer { midi(AUEventSampleTimeImmediate, 0, 3, $0.baseAddress!) }
        i += 1
    }
    try renderFrames(AVAudioFramePosition(block), into: outFile)
    RunLoop.main.run(until: Date(timeIntervalSinceNow: Double(block) / sr * 0.25))
}
engine.stop()
outFile.close()
if let path = ProcessInfo.processInfo.environment["DSHOST_SAVE_STATE"],
   let d = unit.auAudioUnit.fullState?["jucePluginState"] as? Data, let x = decodeJuce(d) {
    try x.write(toFile: path, atomically: true, encoding: .utf8)
}
print("rendered \(Double(t - start) / sr) s")
