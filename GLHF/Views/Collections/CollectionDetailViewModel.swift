//
//  CollectionDetailViewModel.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation
import SwiftData

enum CollectionFilterMode: String, CaseIterable, Identifiable {
    case all = "All"
    case owned = "Owned"
    case missing = "Missing"

    var id: String { rawValue }
}

@Observable
@MainActor
final class CollectionDetailViewModel {
    let collection: GameCollection

    var filterMode: CollectionFilterMode = .all
    var searchText = ""

    var filteredGames: [RAWGGame] = []
    var manualGames: [RAWGGame] = []
    var totalCount: Int = 0
    var isLoading = false
    var isLoadingMore = false
    var errorMessage: String?

    private var currentPage = 0
    private var hasMorePages = true
    private let pageSize = 20
    private let service = RAWGService()

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

    var games: [RAWGGame] {
        let manualIds = Set(manualGames.map { game in game.id })
        let uniqueFiltered = filteredGames.filter { game in
            !manualIds.contains(game.id)
        }
        return manualGames + uniqueFiltered
    }

    var displayedGames: [RAWGGame] {
        let excluded = Set(collection.excludedAPIIds)
        let owned = ownedAPIIds

        return games.filter { game in
            guard !excluded.contains(game.id) else { return false }

            switch filterMode {
            case .all:
                break
            case .owned:
                if !owned.contains(game.id) { return false }
            case .missing:
                if owned.contains(game.id) { return false }
            }

            if !searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return game.name.localizedCaseInsensitiveContains(searchText)
            }

            return true
        }
    }

    func loadInitialGames() async {
        await loadManualGames()

        guard collection.hasFilters else { return }
        guard filteredGames.isEmpty else { return }

        currentPage = 0
        hasMorePages = true
        await loadNextPage()
    }

    func refresh() async {
        filteredGames = []
        manualGames = []
        currentPage = 0
        hasMorePages = true
        errorMessage = nil

        await loadManualGames()

        if collection.hasFilters {
            await loadNextPage()
        }
    }

    private func loadManualGames() async {
        let ids = collection.includedAPIIds
        guard !ids.isEmpty else {
            manualGames = []
            return
        }

        do {
            manualGames = try await service.getGames(byIds: ids)
        } catch {
            manualGames = []
        }
    }

    func loadNextPage() async {
        guard collection.hasFilters else { return }
        guard hasMorePages else { return }
        guard !isLoading, !isLoadingMore else { return }

        let nextPage = currentPage + 1

        if filteredGames.isEmpty {
            isLoading = true
        } else {
            isLoadingMore = true
        }
        errorMessage = nil

        do {
            let response = try await service.getGamesByCollection(
                collection,
                page: nextPage,
                pageSize: pageSize
            )

            totalCount = response.count
            filteredGames.append(contentsOf: response.results)
            currentPage = nextPage
            hasMorePages = response.next != nil

            if collection.totalCatalogSize != response.count {
                collection.totalCatalogSize = response.count
                collection.lastSyncedAt = Date()
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
        isLoadingMore = false
    }

    func shouldLoadMore(for game: RAWGGame) -> Bool {
        guard let lastGame = filteredGames.last else { return false }
        return game.id == lastGame.id && hasMorePages && !isLoadingMore
    }

    func exclude(_ game: RAWGGame, modelContext: ModelContext) {
        if !collection.excludedAPIIds.contains(game.id) {
            collection.excludedAPIIds.append(game.id)
        }

        if let entry = collection.entries.first(where: { existing in
            existing.game?.apiId == game.id
        }) {
            modelContext.delete(entry)
        }
    }

    func entry(for game: RAWGGame) -> CollectionEntry? {
        collection.entries.first { entry in
            entry.game?.apiId == game.id
        }
    }
}
