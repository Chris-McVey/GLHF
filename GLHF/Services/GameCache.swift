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

    static func findOrCreate(
        catalogGame: CanonicalBundleGame,
        rawgGame: RAWGGame?,
        in modelContext: ModelContext
    ) -> Game {
        let apiId = catalogGame.apiId
        let fetchDescriptor = FetchDescriptor<Game>(
            predicate: #Predicate { existingGame in
                existingGame.apiId == apiId
            }
        )

        if let existing = try? modelContext.fetch(fetchDescriptor).first {
            if let rawgGame, existing.coverImageURL == nil {
                existing.coverImageURL = rawgGame.backgroundImage
            }
            return existing
        }

        let title = rawgGame?.name ?? catalogGame.name
        let newGame = Game(
            apiId: apiId,
            title: title,
            coverImageURL: rawgGame?.backgroundImage,
            summary: rawgGame?.description?.strippingHTML(),
            platforms: rawgGame?.platformNames ?? "Nintendo Entertainment System",
            releaseDate: rawgGame?.releaseDate ?? catalogGame.releaseDate,
            genres: rawgGame?.genreNames
        )
        modelContext.insert(newGame)
        return newGame
    }
}

private extension CanonicalBundleGame {
    var releaseDate: Date? {
        guard let releaseYear else { return nil }
        var components = DateComponents()
        components.year = releaseYear
        components.month = 1
        components.day = 1
        return Calendar.current.date(from: components)
    }
}
