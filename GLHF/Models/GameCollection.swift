//
//  GameCollection.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation
import SwiftData

@Model
final class GameCollection {
    var name: String
    var icon: String
    var createdAt: Date

    var platformID: Int?
    var platformName: String?
    var genreID: Int?
    var genreName: String?
    var developerID: Int?
    var developerName: String?
    var searchQuery: String?
    var dateFromYear: Int?
    var dateToYear: Int?

    var totalCatalogSize: Int = 0
    var lastSyncedAt: Date?

    var excludedAPIIds: [Int] = []
    var includedAPIIds: [Int] = []

    /// Bundled canonical set identifier (e.g. `nes-20260518`).
    var canonicalSetID: String?
    var canonicalSetVersion: String?

    @Relationship(deleteRule: .cascade, inverse: \CollectionEntry.collection)
    var entries: [CollectionEntry] = []

    var isCanonicalBased: Bool {
        canonicalSetID != nil
    }

    var ownedEntries: [CollectionEntry] {
        entries.filter { entry in entry.owned }
    }

    var ownedCount: Int {
        ownedEntries.count
    }

    var gameCount: Int {
        entries.count
    }

    var totalValue: Double {
        ownedEntries.reduce(0) { runningTotal, entry in
            runningTotal + (entry.value ?? 0)
        }
    }

    var completionPercent: Double {
        guard totalCatalogSize > 0 else { return 0 }
        return Double(ownedCount) / Double(totalCatalogSize) * 100
    }

    var hasFilters: Bool {
        guard !isCanonicalBased else { return false }
        return platformID != nil
            || genreID != nil
            || developerID != nil
            || (searchQuery?.isEmpty == false)
            || dateFromYear != nil
            || dateToYear != nil
    }

    init(name: String, icon: String = "folder") {
        self.name = name
        self.icon = icon
        self.createdAt = Date()
    }
}
