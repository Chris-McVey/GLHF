//
//  DeveloperPickerView.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI

struct DeveloperPickerView: View {
    let onSelect: (RAWGDeveloper) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var searchText = ""
    @State private var developers: [RAWGDeveloper] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var searchTask: Task<Void, Never>?

    private let service = RAWGService()

    var body: some View {
        content
            .navigationTitle("Developer")
            .navigationBarTitleDisplayMode(.inline)
            .searchable(text: $searchText, prompt: "Search developers")
            .onChange(of: searchText) {
                scheduleSearch()
            }
    }

    @ViewBuilder
    private var content: some View {
        if searchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            ContentUnavailableView(
                "Search Developers",
                systemImage: "magnifyingglass",
                description: Text("Type a developer's name to find them")
            )
        } else if isLoading && developers.isEmpty {
            ProgressView("Searching...")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let errorMessage {
            ContentUnavailableView(
                "Search Failed",
                systemImage: "exclamationmark.triangle",
                description: Text(errorMessage)
            )
        } else if developers.isEmpty {
            ContentUnavailableView(
                "No Developers Found",
                systemImage: "person.crop.circle.badge.questionmark",
                description: Text("Try a different search")
            )
        } else {
            List(developers) { developer in
                Button {
                    onSelect(developer)
                    dismiss()
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(developer.name)
                                .font(.body)
                                .foregroundStyle(.primary)

                            Text("\(developer.gamesCount) games")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        Image(systemName: "chevron.right")
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                    }
                }
            }
        }
    }

    private func scheduleSearch() {
        searchTask?.cancel()

        let trimmed = searchText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            developers = []
            errorMessage = nil
            isLoading = false
            return
        }

        searchTask = Task {
            try? await Task.sleep(for: .milliseconds(400))
            if Task.isCancelled { return }
            await performSearch(query: trimmed)
        }
    }

    private func performSearch(query: String) async {
        isLoading = true
        errorMessage = nil

        do {
            let results = try await service.searchDevelopers(query: query)
            if Task.isCancelled { return }
            developers = results
        } catch {
            if Task.isCancelled { return }
            errorMessage = error.localizedDescription
            developers = []
        }

        isLoading = false
    }
}
