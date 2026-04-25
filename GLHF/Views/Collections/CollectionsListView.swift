//
//  CollectionsListView.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct CollectionsListView: View {
    @Query(sort: \GameCollection.createdAt, order: .reverse) private var collections: [GameCollection]
    @Environment(\.modelContext) private var modelContext
    @State private var showingCreateSheet = false

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Collections")
                .toolbar {
                    ToolbarItem(placement: .primaryAction) {
                        Button {
                            showingCreateSheet = true
                        } label: {
                            Label("New Collection", systemImage: "plus")
                        }
                    }
                }
                .sheet(isPresented: $showingCreateSheet) {
                    CreateCollectionView()
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        if collections.isEmpty {
            ContentUnavailableView(
                "No Collections Yet",
                systemImage: "square.stack.3d.up",
                description: Text("Tap + to create a smart or custom collection")
            )
        } else {
            List {
                ForEach(collections) { collection in
                    NavigationLink(destination: CollectionDetailView(collection: collection)) {
                        collectionRow(collection)
                    }
                }
                .onDelete(perform: deleteCollections)
            }
        }
    }

    private func collectionRow(_ collection: GameCollection) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: collection.icon)
                .font(.title2)
                .foregroundStyle(.tint)
                .frame(width: 36, height: 36)
                .background(Color.accentColor.opacity(0.12))
                .clipShape(RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading, spacing: 6) {
                Text(collection.name)
                    .font(.headline)

                if collection.hasFilters {
                    smartCollectionSubtitle(collection)
                } else {
                    Text("\(collection.gameCount) games")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }

    @ViewBuilder
    private func smartCollectionSubtitle(_ collection: GameCollection) -> some View {
        if !filterTags(collection).isEmpty {
            Text(filterTags(collection))
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }

        if collection.totalCatalogSize > 0 {
            VStack(alignment: .leading, spacing: 2) {
                ProgressView(value: collection.completionPercent / 100)
                    .tint(.accentColor)

                HStack {
                    Text("\(collection.ownedCount) of \(collection.totalCatalogSize) owned")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("\(Int(collection.completionPercent))%")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.tint)
                }
            }
        } else {
            Text("\(collection.ownedCount) owned")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func filterTags(_ collection: GameCollection) -> String {
        var parts: [String] = []
        if let platform = collection.platformName { parts.append(platform) }
        if let genre = collection.genreName { parts.append(genre) }
        if let developer = collection.developerName { parts.append(developer) }
        return parts.joined(separator: " · ")
    }

    private func deleteCollections(offsets: IndexSet) {
        for index in offsets {
            modelContext.delete(collections[index])
        }
    }
}

#Preview {
    CollectionsListView()
        .modelContainer(
            for: [Game.self, GameCollection.self, CollectionEntry.self],
            inMemory: true
        )
}
