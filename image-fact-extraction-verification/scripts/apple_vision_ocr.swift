#!/usr/bin/env swift

import AppKit
import Foundation
import Vision

func fail(_ message: String, code: Int32 = 1) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(code)
}

guard CommandLine.arguments.count == 2 else {
    fail("usage: apple_vision_ocr.swift IMAGE")
}

let imagePath = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: imagePath) else {
    fail("cannot load image: \(imagePath)")
}

var proposedRect = NSRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &proposedRect, context: nil, hints: nil) else {
    fail("cannot convert image to CGImage: \(imagePath)")
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true
request.minimumTextHeight = 0.003

do {
    try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
} catch {
    fail("Vision OCR failed: \(error)")
}

let observations = (request.results ?? []).compactMap { $0 as? VNRecognizedTextObservation }
let rows: [[String: Any]] = observations.compactMap { observation in
    guard let candidate = observation.topCandidates(1).first else { return nil }
    let box = observation.boundingBox
    return [
        "text": candidate.string,
        "confidence": Double(candidate.confidence),
        "bbox": [
            "x": Double(box.origin.x),
            "y": Double(box.origin.y),
            "width": Double(box.width),
            "height": Double(box.height),
            "top": Double(1.0 - box.origin.y - box.height)
        ]
    ]
}.sorted { lhs, rhs in
    let leftBox = lhs["bbox"] as! [String: Double]
    let rightBox = rhs["bbox"] as! [String: Double]
    let verticalDelta = abs(leftBox["top"]! - rightBox["top"]!)
    if verticalDelta > 0.01 { return leftBox["top"]! < rightBox["top"]! }
    return leftBox["x"]! < rightBox["x"]!
}

let payload: [String: Any] = [
    "engine": "Apple Vision",
    "image": imagePath,
    "width": cgImage.width,
    "height": cgImage.height,
    "observations": rows
]

do {
    let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write("\n".data(using: .utf8)!)
} catch {
    fail("cannot serialize OCR result: \(error)")
}
