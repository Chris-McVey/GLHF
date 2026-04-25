//
//  AddToCollectionSheet.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct AddToCollectionSheet: View {
    let game: RAWGGame
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss
    @Query(sort: \GameCollection.createdAt, order: .reverse) private var collections: [GameCollection]

    @State private var selectedCollection: GameCollection?
    @State private var owned = true
    @State private var value: Double?
    @State private var condition: String?
    @State private var notes = ""
    @State private var showingCreateCollection = false

    private let conditionOptions = ["New", "Like New", "Good", "Fair", "Poor"]

    private var isValid: Bool {
        selectedCollection != nil
    }

    var body: some View {
        NavigationStack {
            Form {
                collectionSection
                ownershipSection

                if owned {
                    valueSection
                    conditionSection
                }

                notesSection
            }
            .navigationTitle("Add to Collection")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") { addToCollection() }
                        .disabled(!isValid)
                }
            }
            .sheet(isPresented: $showingCreateCollection) {
                CreateCollectionView()
            }
        }
    }

    private var collectionSection: some View {
        Section("Collection") {
            if collections.isEmpty {
                Text("No collections yet")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(collections, id: \.persistentModelID) { (collection: GameCollection) in
                    Button {
                        selectedCollection = collection
                    } label: {
                        HStack {
                            Image(systemName: collection.icon)
                                .frame(width: 24)

                            Text(collection.name)
                                .foregroundStyle(.primary)

                            Spacer()

                            if selectedCollection === collection {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(.tint)
                            }
                        }
                    }
                }
            }

            Button {
                showingCreateCollection = true
            } label: {
                Label("Create New Collection", systemImage: "plus.circle")
            }
        }
    }

    private var ownershipSection: some View {
        Section {
            Toggle("I own this game", isOn: $owned)
        } footer: {
            Text(owned ? "This game will count toward your collection's progress." : "Tracked as a wishlist item.")
        }
    }

    private var valueSection: some View {
        Section("Value (optional)") {
            HStack {
                Text("$")
                TextField("0.00", value: $value, format: .number.precision(.fractionLength(2)))
                    .keyboardType(.decimalPad)
            }
        }
    }

    private var conditionSection: some View {
        Section("Condition (optional)") {
            Picker("Condition", selection: $condition) {
                Text("Not set").tag(String?.none)
                ForEach(conditionOptions, id: \.self) { option in
                    Text(option).tag(String?.some(option))
                }
            }
        }
    }

    private var notesSection: some View {
        Section("Notes (optional)") {
            TextEditor(text: $notes)
                .frame(minHeight: 80)
        }
    }

    private func addToCollection() {
        guard let selectedCollection else { return }

        let cachedGame = GameCache.findOrCreate(from: game, in: modelContext)
        let trimmedNotes = notes.trimmingCharacters(in: .whitespacesAndNewlines)

        let entry = CollectionEntry(
            owned: owned,
            value: value,
            condition: condition,
            notes: trimmedNotes.isEmpty ? nil : trimmedNotes,
            game: cachedGame,
            collection: selectedCollection
        )
        modelContext.insert(entry)

        if !selectedCollection.includedAPIIds.contains(game.id) {
            selectedCollection.includedAPIIds.append(game.id)
        }

        dismiss()
    }
}
