//
//  DiscoverView.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct DiscoverView: View {
    @State private var viewModel = DiscoverViewModel()
    @Environment(\.modelContext) private var modelContext

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    ProgressView("Searching...")
                } else if let errorMessage = viewModel.errorMessage {
                    ContentUnavailableView(
                        "Something Went Wrong",
                        systemImage: "exclamationmark.triangle",
                        description: Text(errorMessage)
                    )
                } else if viewModel.games.isEmpty && !viewModel.searchText.isEmpty {
                    ContentUnavailableView.search(text: viewModel.searchText)
                } else if viewModel.games.isEmpty {
                    ContentUnavailableView(
                        "Search for Games",
                        systemImage: "magnifyingglass",
                        description: Text("Find games to review and add to your collection")
                    )
                } else {
                    List(viewModel.games) { game in
                        NavigationLink(destination: GameDetailView(game: game, modelContext: modelContext)) {
                            GameCardView(game: game)
                        }
                    }
                }
            }
            .navigationTitle("Discover")
            .searchable(text: $viewModel.searchText, prompt: "Search games...")
            .onSubmit(of: .search) {
                Task {
                    await viewModel.searchGames()
                }
            }
        }
    }
}

#Preview {
    DiscoverView()
        .modelContainer(
            for: [Game.self, Review.self, GameCollection.self, CollectionEntry.self],
            inMemory: true
        )
}
