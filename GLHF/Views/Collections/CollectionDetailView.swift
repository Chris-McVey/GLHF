//
//  CollectionDetailView.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct CollectionDetailView: View {
    let collection: GameCollection
    @Environment(\.modelContext) private var modelContext
    @State private var viewModel: CollectionDetailViewModel?
    @State private var selectedGame: RAWGGame?

    var body: some View {
        content
            .navigationTitle(collection.name)
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $selectedGame) { game in
                CollectionGameDetailView(game: game, collection: collection)
            }
            .task {
                if viewModel == nil {
                    viewModel = CollectionDetailViewModel(collection: collection)
                    await viewModel?.loadInitialGames()
                }
            }
    }

    @ViewBuilder
    private var content: some View {
        if collection.hasFilters {
            smartCollectionContent
        } else {
            manualCollectionContent
        }
    }

    @ViewBuilder
    private var smartCollectionContent: some View {
        if let viewModel {
            @Bindable var vm = viewModel

            VStack(spacing: 0) {
                progressHeader(vm: viewModel)

                Picker("Filter", selection: $vm.filterMode) {
                    ForEach(CollectionFilterMode.allCases) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.bottom, 8)

                gamesList(vm: viewModel)
            }
            .searchable(text: $vm.searchText, prompt: "Search in collection")
        } else {
            ProgressView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func progressHeader(vm: CollectionDetailViewModel) -> some View {
        let total = collection.totalCatalogSize > 0 ? collection.totalCatalogSize : vm.totalCount
        let owned = vm.ownedCount
        let percent = total > 0 ? Double(owned) / Double(total) : 0

        return VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .firstTextBaseline) {
                Text("\(owned)")
                    .font(.largeTitle.weight(.bold))
                Text("of \(total) owned")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Spacer()
                Text("\(Int(percent * 100))%")
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.tint)
            }

            ProgressView(value: percent)
                .tint(.accentColor)
        }
        .padding()
    }

    @ViewBuilder
    private func gamesList(vm: CollectionDetailViewModel) -> some View {
        if vm.isLoading && vm.games.isEmpty {
            ProgressView("Loading games...")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let error = vm.errorMessage, vm.games.isEmpty {
            ContentUnavailableView(
                "Couldn't Load Games",
                systemImage: "exclamationmark.triangle",
                description: Text(error)
            )
        } else if vm.displayedGames.isEmpty {
            emptyStateForMode(mode: vm.filterMode)
        } else {
            List {
                ForEach(vm.displayedGames) { game in
                    gameRow(game, vm: vm)
                        .onAppear {
                            if vm.shouldLoadMore(for: game) {
                                Task { await vm.loadNextPage() }
                            }
                        }
                        .swipeActions(edge: .trailing) {
                            Button(role: .destructive) {
                                vm.exclude(game, modelContext: modelContext)
                            } label: {
                                Label("Exclude", systemImage: "xmark.circle")
                            }
                        }
                }

                if vm.isLoadingMore {
                    HStack {
                        Spacer()
                        ProgressView()
                        Spacer()
                    }
                    .listRowSeparator(.hidden)
                }
            }
            .listStyle(.plain)
        }
    }

    private func gameRow(_ game: RAWGGame, vm: CollectionDetailViewModel) -> some View {
        let isOwned = vm.ownedAPIIds.contains(game.id)

        return Button {
            selectedGame = game
        } label: {
            HStack(spacing: 12) {
                cover(for: game)

                VStack(alignment: .leading, spacing: 4) {
                    Text(game.name)
                        .font(.headline)
                        .foregroundStyle(.primary)
                        .lineLimit(2)

                    if let released = game.released {
                        Text(released.prefix(4))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                Image(systemName: isOwned ? "checkmark.circle.fill" : "circle")
                    .font(.title2)
                    .foregroundStyle(isOwned ? Color.accentColor : Color.secondary)
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private func cover(for game: RAWGGame) -> some View {
        Group {
            if let urlString = game.backgroundImage, let url = URL(string: urlString) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image.resizable().scaledToFill()
                    default:
                        placeholderCover
                    }
                }
            } else {
                placeholderCover
            }
        }
        .frame(width: 60, height: 60)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var placeholderCover: some View {
        ZStack {
            Color.gray.opacity(0.2)
            Image(systemName: "gamecontroller")
                .foregroundStyle(.secondary)
        }
    }

    @ViewBuilder
    private func emptyStateForMode(mode: CollectionFilterMode) -> some View {
        switch mode {
        case .all:
            ContentUnavailableView("No Games", systemImage: "gamecontroller")
        case .owned:
            ContentUnavailableView(
                "Nothing Owned Yet",
                systemImage: "checkmark.circle",
                description: Text("Tap games in the All tab to mark them owned")
            )
        case .missing:
            ContentUnavailableView(
                "Complete!",
                systemImage: "trophy",
                description: Text("You own every game in this collection")
            )
        }
    }

    @ViewBuilder
    private var manualCollectionContent: some View {
        if collection.entries.isEmpty {
            ContentUnavailableView(
                "No Games Yet",
                systemImage: "gamecontroller",
                description: Text("Add games from the Discover tab")
            )
        } else {
            List {
                ForEach(collection.entries) { entry in
                    manualEntryRow(entry)
                }
                .onDelete(perform: deleteManualEntries)
            }
        }
    }

    private func manualEntryRow(_ entry: CollectionEntry) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(entry.game?.title ?? "Unknown Game")
                    .font(.headline)

                HStack(spacing: 8) {
                    if !entry.owned {
                        Text("Wishlist")
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(.fill)
                            .clipShape(Capsule())
                    }

                    if let condition = entry.condition {
                        Text(condition)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Spacer()

            if let value = entry.value {
                Text(value, format: .currency(code: "USD"))
                    .font(.subheadline)
                    .fontWeight(.medium)
            }
        }
    }

    private func deleteManualEntries(offsets: IndexSet) {
        for index in offsets {
            modelContext.delete(collection.entries[index])
        }
    }
}
