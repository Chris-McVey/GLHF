//
//  GameCache.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation
import SwiftData

enum GameCache {
    static func findOrCreate(from rawgGame: RAWGGame, in modelContext: ModelContext) -> Game {
        let apiId = rawgGame.id
        let fetchDescriptor = FetchDescriptor<Game>(
            predicate: #Predicate { existingGame in
                existingGame.apiId == apiId
            }
        )

        if let existing = try? modelContext.fetch(fetchDescriptor).first {
            return existing
        }

        let newGame = Game(
            apiId: rawgGame.id,
            title: rawgGame.name,
            coverImageURL: rawgGame.backgroundImage,
            summary: rawgGame.description?.strippingHTML(),
            platforms: rawgGame.platformNames,
            releaseDate: rawgGame.releaseDate,
            genres: rawgGame.genreNames
        )
        modelContext.insert(newGame)
        return newGame
    }
}
