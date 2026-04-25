//
//  CollectionGameDetailView.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct CollectionGameDetailView: View {
    let game: RAWGGame
    let collection: GameCollection
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss

    @State private var owned = false
    @State private var value: Double?
    @State private var condition: String?
    @State private var notes = ""

    private let conditionOptions = ["New", "Like New", "Good", "Fair", "Poor"]

    var body: some View {
        NavigationStack {
            Form {
                headerSection
                ownershipSection

                if owned {
                    valueSection
                    conditionSection
                }

                notesSection
            }
            .navigationTitle(game.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                }
            }
            .onAppear(perform: loadExisting)
        }
    }

    @ViewBuilder
    private var headerSection: some View {
        Section {
            if let urlString = game.backgroundImage, let url = URL(string: urlString) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFill()
                    default:
                        Color.gray.opacity(0.2)
                    }
                }
                .frame(height: 180)
                .frame(maxWidth: .infinity)
                .clipped()
                .listRowInsets(EdgeInsets())
            }

            if let released = game.released {
                LabeledContent("Released", value: released)
            }

            if !game.platformNames.isEmpty {
                LabeledContent("Platforms", value: game.platformNames)
            }
        }
    }

    private var ownershipSection: some View {
        Section {
            Toggle("I own this game", isOn: $owned)
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
        Section("Notes") {
            TextEditor(text: $notes)
                .frame(minHeight: 80)
        }
    }

    private func loadExisting() {
        guard let entry = existingEntry() else { return }

        owned = entry.owned
        value = entry.value
        condition = entry.condition
        notes = entry.notes ?? ""
    }

    private func existingEntry() -> CollectionEntry? {
        collection.entries.first { entry in
            entry.game?.apiId == game.id
        }
    }

    private func save() {
        let trimmedNotes = notes.trimmingCharacters(in: .whitespacesAndNewlines)
        let hasData = owned || !trimmedNotes.isEmpty

        if let entry = existingEntry() {
            if hasData {
                entry.owned = owned
                entry.value = value
                entry.condition = condition
                entry.notes = trimmedNotes.isEmpty ? nil : trimmedNotes
            } else {
                modelContext.delete(entry)
            }
        } else if hasData {
            let cachedGame = GameCache.findOrCreate(from: game, in: modelContext)
            let entry = CollectionEntry(
                owned: owned,
                value: value,
                condition: condition,
                notes: trimmedNotes.isEmpty ? nil : trimmedNotes,
                game: cachedGame,
                collection: collection
            )
            modelContext.insert(entry)
        }

        dismiss()
    }
}
