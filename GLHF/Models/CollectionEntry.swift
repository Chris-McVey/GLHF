//
//  CollectionEntry.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation
import SwiftData

@Model
final class CollectionEntry {
    var owned: Bool
    var value: Double?
    var condition: String?
    var notes: String?
    var addedAt: Date

    var game: Game?
    var collection: GameCollection?

    init(
        owned: Bool = true,
        value: Double? = nil,
        condition: String? = nil,
        notes: String? = nil,
        game: Game? = nil,
        collection: GameCollection? = nil
    ) {
        self.owned = owned
        self.value = value
        self.condition = condition
        self.notes = notes
        self.addedAt = Date()
        self.game = game
        self.collection = collection
    }
}
