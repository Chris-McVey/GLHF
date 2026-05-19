//
//  CanonicalCollectionDetailViewModel.swift
//  GLHF
//

import Foundation
import SwiftData

@Observable
@MainActor
final class CanonicalCollectionDetailViewModel {
    let collection: GameCollection

    var filterMode: CollectionFilterMode = .all
    var searchText = ""
    var catalogGames: [CollectionCatalogGame] = []
    var isLoading = false
    var errorMessage: String?
    var attribution: String?

    private let rawgService = RAWGService()

    init(collection: GameCollection) {
        self.collection = collection
    }

    var ownedAPIIds: Set<Int> {
        Set(collection.entries.compactMap { entry in
            entry.owned ? entry.game?.apiId : nil
        })
    }

    var ownedCount: Int {
        ownedAPIIds.count
    }

    var displayedGames: [CollectionCatalogGame] {
        let owned = ownedAPIIds
        return catalogGames.filter { item in
            switch filterMode {
            case .all:
                break
            case .owned:
                if !owned.contains(item.id) { return false }
            case .missing:
                if owned.contains(item.id) { return false }
            }

            if !searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return item.name.localizedCaseInsensitiveContains(searchText)
            }
            return true
        }
    }

    func load() async {
        guard catalogGames.isEmpty else { return }
        isLoading = true
        errorMessage = nil

        guard let bundle = CanonicalSetService.loadBundle(for: collection) else {
            errorMessage = "Couldn't load the canonical game list for this collection."
            isLoading = false
            return
        }

        attribution = CanonicalSetService.availablePresets()
            .first { $0.id == collection.canonicalSetID }?.attribution

        let bundleGames = bundle.games
        var rawgByID: [Int: RAWGGame] = [:]
        let rawgIDs = bundleGames.compactMap(\.rawgID)

        if !rawgIDs.isEmpty {
            do {
                let fetched = try await rawgService.getGames(byIds: rawgIDs)
                for game in fetched {
                    rawgByID[game.id] = game
                }
            } catch {
                // List still works from bundle metadata without covers.
            }
        }

        catalogGames = bundleGames.map { bundleGame in
            let rawg = bundleGame.rawgID.flatMap { rawgByID[$0] }
            return CollectionCatalogGame(bundleGame: bundleGame, rawgGame: rawg)
        }
        .sorted { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }

        if collection.totalCatalogSize != bundle.gameCount {
            collection.totalCatalogSize = bundle.gameCount
        }

        isLoading = false
    }

    func isOwned(_ item: CollectionCatalogGame) -> Bool {
        ownedAPIIds.contains(item.id)
    }

    func entry(for item: CollectionCatalogGame) -> CollectionEntry? {
        collection.entries.first { $0.game?.apiId == item.id }
    }

    func toggleOwned(_ item: CollectionCatalogGame, modelContext: ModelContext) {
        if let entry = entry(for: item), entry.owned {
            modelContext.delete(entry)
            return
        }

        let cachedGame = GameCache.findOrCreate(
            catalogGame: item.bundleGame,
            rawgGame: item.rawgGame,
            in: modelContext
        )
        let entry = CollectionEntry(owned: true, game: cachedGame, collection: collection)
        modelContext.insert(entry)
    }
}
