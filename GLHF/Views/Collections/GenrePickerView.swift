//
//  GenrePickerView.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI

struct GenrePickerView: View {
    let onSelect: (RAWGGenre) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var genres: [RAWGGenre] = []
    @State private var isLoading = false
    @State private var errorMessage: String?

    private let service = RAWGService()

    var body: some View {
        content
            .navigationTitle("Genre")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                await loadGenres()
            }
    }

    @ViewBuilder
    private var content: some View {
        if isLoading && genres.isEmpty {
            ProgressView("Loading genres...")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let errorMessage {
            ContentUnavailableView(
                "Couldn't Load Genres",
                systemImage: "exclamationmark.triangle",
                description: Text(errorMessage)
            )
        } else {
            List(genres) { genre in
                Button {
                    onSelect(genre)
                    dismiss()
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(genre.name)
                                .font(.body)
                                .foregroundStyle(.primary)

                            if let count = genre.gamesCount {
                                Text("\(count) games")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
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

    private func loadGenres() async {
        guard genres.isEmpty else { return }

        isLoading = true
        errorMessage = nil

        do {
            let fetched = try await service.getGenres()
            genres = fetched.sorted { left, right in
                (left.gamesCount ?? 0) > (right.gamesCount ?? 0)
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}
