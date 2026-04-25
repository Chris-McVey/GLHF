//
//  DiscoverViewModel.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation

@Observable
final class DiscoverViewModel {
    var searchText = ""
    var games: [RAWGGame] = []
    var isLoading = false
    var errorMessage: String?

    private let service = RAWGService()

    func searchGames() async {
        let trimmed = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            games = []
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            games = try await service.searchGames(query: trimmed)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}
