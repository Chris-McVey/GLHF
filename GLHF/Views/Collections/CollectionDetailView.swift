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
    @State private var smartViewModel: CollectionDetailViewModel?
    @State private var canonicalViewModel: CanonicalCollectionDetailViewModel?
    @State private var selectedGame: RAWGGame?
    @State private var selectedPlaceholder: CollectionCatalogGame?

    var body: some View {
        content
            .navigationTitle(collection.name)
            .navigationBarTitleDisplayMode(.inline)
            .sheet(item: $selectedGame) { game in
                CollectionGameDetailView(game: game, collection: collection)
            }
            .sheet(item: $selectedPlaceholder) { item in
                CollectionPlaceholderGameDetailView(item: item, collection: collection)
            }
            .task {
                if collection.isCanonicalBased {
                    if canonicalViewModel == nil {
                        canonicalViewModel = CanonicalCollectionDetailViewModel(collection: collection)
                        await canonicalViewModel?.load()
                    }
                } else if collection.hasFilters {
                    if smartViewModel == nil {
                        smartViewModel = CollectionDetailViewModel(collection: collection)
                        await smartViewModel?.loadInitialGames()
                    }
                }
            }
    }

    @ViewBuilder
    private var content: some View {
        if collection.isCanonicalBased {
            canonicalCollectionContent
        } else if collection.hasFilters {
            smartCollectionContent
        } else {
            manualCollectionContent
        }
    }

    // MARK: - Canonical collection

    @ViewBuilder
    private var canonicalCollectionContent: some View {
        if let canonicalViewModel {
            @Bindable var vm = canonicalViewModel

            VStack(spacing: 0) {
                progressHeader(owned: vm.ownedCount, total: catalogTotal)

                Picker("Filter", selection: $vm.filterMode) {
                    ForEach(CollectionFilterMode.allCases) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.bottom, 8)

                canonicalGamesList(vm: canonicalViewModel)
            }
            .searchable(text: $vm.searchText, prompt: "Search in collection")
        } else {
            ProgressView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var catalogTotal: Int {
        if collection.totalCatalogSize > 0 {
            return collection.totalCatalogSize
        }
        return canonicalViewModel?.catalogGames.count ?? 0
    }

    @ViewBuilder
    private func canonicalGamesList(vm: CanonicalCollectionDetailViewModel) -> some View {
        if vm.isLoading && vm.catalogGames.isEmpty {
            ProgressView("Loading checklist...")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let error = vm.errorMessage, vm.catalogGames.isEmpty {
            ContentUnavailableView(
                "Couldn't Load Checklist",
                systemImage: "exclamationmark.triangle",
                description: Text(error)
            )
        } else if vm.displayedGames.isEmpty {
            emptyStateForMode(mode: vm.filterMode)
        } else {
            List {
                ForEach(vm.displayedGames) { item in
                    canonicalGameRow(item, vm: vm)
                }

                if let attribution = vm.attribution {
                    Section {
                        Text(attribution)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .listStyle(.plain)
        }
    }

    private func canonicalGameRow(
        _ item: CollectionCatalogGame,
        vm: CanonicalCollectionDetailViewModel
    ) -> some View {
        let isOwned = vm.isOwned(item)

        return Button {
            if let rawg = item.rawgGame {
                selectedGame = rawg
            } else {
                selectedPlaceholder = item
            }
        } label: {
            HStack(spacing: 12) {
                canonicalCover(for: item)

                VStack(alignment: .leading, spacing: 4) {
                    Text(item.name)
                        .font(.headline)
                        .foregroundStyle(.primary)
                        .lineLimit(2)

                    HStack(spacing: 4) {
                        if let year = item.releaseYear {
                            Text(String(year))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        if item.isPlaceholderOnly {
                            Text(item.releaseYear != nil ? "· Checklist only" : "Checklist only")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
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

    @ViewBuilder
    private func canonicalCover(for item: CollectionCatalogGame) -> some View {
        Group {
            if let urlString = item.rawgGame?.backgroundImage, let url = URL(string: urlString) {
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

    // MARK: - Smart collection

    @ViewBuilder
    private var smartCollectionContent: some View {
        if let smartViewModel {
            @Bindable var vm = smartViewModel

            VStack(spacing: 0) {
                progressHeader(
                    owned: smartViewModel.ownedCount,
                    total: collection.totalCatalogSize > 0
                        ? collection.totalCatalogSize
                        : smartViewModel.totalCount
                )

                Picker("Filter", selection: $vm.filterMode) {
                    ForEach(CollectionFilterMode.allCases) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.bottom, 8)

                gamesList(vm: smartViewModel)
            }
            .searchable(text: $vm.searchText, prompt: "Search in collection")
        } else {
            ProgressView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func progressHeader(owned: Int, total: Int) -> some View {
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

    // MARK: - Manual collection

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
