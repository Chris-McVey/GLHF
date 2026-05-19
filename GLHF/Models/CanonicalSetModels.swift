//
//  CanonicalSetModels.swift
//  GLHF
//

import Foundation

struct CanonicalSetBundle: Codable {
    let id: String
    let displayName: String
    let platformName: String
    let platformSlug: String
    let region: String
    let version: String
    let schemaVersion: Int
    let primarySource: String?
    let policy: String?
    let wikipediaListUrl: String?
    let gameCount: Int
    let matchedGameCount: Int?
    let games: [CanonicalBundleGame]
}

struct CanonicalBundleGame: Codable, Identifiable {
    let name: String
    let releaseYear: Int?
    let releaseYearSource: String?
    let publishers: [String]
    let developers: [String]
    let licenseStatus: String?
    let rawgID: Int?
    let rawgName: String?
    let wikidataQID: String?

    var id: String { catalogKey }

    var catalogKey: String {
        CanonicalGameID.catalogKey(for: name)
    }

    var apiId: Int {
        CanonicalGameID.apiId(rawgID: rawgID, catalogKey: catalogKey)
    }
}

/// Preset shown in the create-collection picker.
struct CanonicalSetPreset: Identifiable {
    let id: String
    let version: String
    let displayName: String
    let platformName: String
    let gameCount: Int
    let primarySource: String?
    let wikipediaListUrl: String?
    let attribution: String
}

/// Row model for canonical collection lists (RAWG-backed or placeholder).
struct CollectionCatalogGame: Identifiable {
    let bundleGame: CanonicalBundleGame
    let rawgGame: RAWGGame?

    var id: Int { bundleGame.apiId }
    var name: String { bundleGame.name }
    var releaseYear: Int? { bundleGame.releaseYear }
    var licenseStatus: String? { bundleGame.licenseStatus }
    var hasRAWGCover: Bool { rawgGame?.backgroundImage != nil }
    var isPlaceholderOnly: Bool { bundleGame.rawgID == nil }
}

enum CanonicalGameID {
    /// NES on RAWG — locked when creating from the bundled NES canonical set.
    static let nesRAWGPlatformID = 49

    static func catalogKey(for name: String) -> String {
        let allowed = CharacterSet.alphanumerics
        var parts: [String] = []
        var current = ""
        for scalar in name.lowercased().unicodeScalars {
            if allowed.contains(scalar) {
                current.append(Character(scalar))
            } else if !current.isEmpty {
                parts.append(current)
                current = ""
            }
        }
        if !current.isEmpty {
            parts.append(current)
        }
        return parts.joined(separator: " ")
    }

    /// Stable `Game.apiId`: positive RAWG IDs when present, else negative synthetic IDs.
    static func apiId(rawgID: Int?, catalogKey: String) -> Int {
        if let rawgID, rawgID > 0 { return rawgID }
        var hash: UInt64 = 5381
        for byte in catalogKey.utf8 {
            hash = ((hash << 5) &+ hash) &+ UInt64(byte)
        }
        let bucket = Int(hash % 900_000_000) + 1
        return -bucket
    }
}
