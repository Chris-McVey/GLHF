//
//  CollectionPlaceholderGameDetailView.swift
//  GLHF
//

import SwiftUI
import SwiftData

/// Detail sheet for canonical-list games without a RAWG ID (bundle metadata only).
struct CollectionPlaceholderGameDetailView: View {
    let item: CollectionCatalogGame
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
                placeholderHeader
                ownershipSection

                if owned {
                    valueSection
                    conditionSection
                }

                notesSection
            }
            .navigationTitle(item.name)
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

    private var placeholderHeader: some View {
        Section {
            ZStack {
                Color.gray.opacity(0.15)
                VStack(spacing: 8) {
                    Image(systemName: "gamecontroller")
                        .font(.largeTitle)
                        .foregroundStyle(.secondary)
                    Text("No cover art in database")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 24)
            }
            .frame(maxWidth: .infinity)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))

            if let year = item.releaseYear {
                LabeledContent("Release year", value: String(year))
            }

            if let license = item.licenseStatus {
                LabeledContent("License", value: license.capitalized)
            }

            if !item.bundleGame.publishers.isEmpty {
                LabeledContent("Publisher", value: item.bundleGame.publishers.joined(separator: ", "))
            }

            if !item.bundleGame.developers.isEmpty {
                LabeledContent("Developer", value: item.bundleGame.developers.joined(separator: ", "))
            }

            LabeledContent("Platform", value: collection.platformName ?? "NES")

            Text("This title is in the Wikipedia canonical list but isn't linked to RAWG, so only checklist details are shown.")
                .font(.caption)
                .foregroundStyle(.secondary)
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
        collection.entries.first { $0.game?.apiId == item.id }
    }

    private func save() {
        let trimmedNotes = notes.trimmingCharacters(in: .whitespacesAndNewlines)
        let hasData = owned || !trimmedNotes.isEmpty || value != nil || condition != nil

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
            let cachedGame = GameCache.findOrCreate(
                catalogGame: item.bundleGame,
                rawgGame: nil,
                in: modelContext
            )
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
