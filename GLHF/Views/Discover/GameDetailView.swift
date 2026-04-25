//
//  GameDetailView.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct GameDetailView: View {
    let game: RAWGGame
    let modelContext: ModelContext
    @State private var showingReviewSheet = false
    @State private var showingCollectionSheet = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                headerImage
                gameInfo
                actionButtons
                descriptionSection
            }
        }
        .navigationTitle(game.name)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showingReviewSheet) {
            WriteReviewView(game: game)
        }
        .sheet(isPresented: $showingCollectionSheet) {
            AddToCollectionSheet(game: game)
        }
    }

    private var actionButtons: some View {
        HStack(spacing: 12) {
            Button {
                showingReviewSheet = true
            } label: {
                Label("Review", systemImage: "square.and.pencil")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)

            Button {
                showingCollectionSheet = true
            } label: {
                Label("Collect", systemImage: "plus.square.on.square")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
        }
        .padding(.horizontal)
    }

    private var headerImage: some View {
        AsyncImage(url: URL(string: game.backgroundImage ?? "")) { phase in
            switch phase {
            case .success(let image):
                image
                    .resizable()
                    .aspectRatio(contentMode: .fill)
            case .failure:
                Rectangle()
                    .fill(.quaternary)
                    .overlay {
                        Image(systemName: "photo")
                            .font(.largeTitle)
                            .foregroundStyle(.secondary)
                    }
            default:
                Rectangle()
                    .fill(.quaternary)
                    .overlay { ProgressView() }
            }
        }
        .frame(height: 220)
        .clipped()
    }

    private var gameInfo: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(game.name)
                .font(.title)
                .fontWeight(.bold)

            HStack(spacing: 16) {
                if let rating = game.rating, rating > 0 {
                    Label(
                        String(format: "%.1f", rating),
                        systemImage: "star.fill"
                    )
                    .foregroundStyle(.yellow)
                }

                if let released = game.released {
                    Label(released, systemImage: "calendar")
                }
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)

            if !game.genreNames.isEmpty {
                Label(game.genreNames, systemImage: "tag")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if !game.platformNames.isEmpty {
                Label(game.platformNames, systemImage: "gamecontroller")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal)
    }

    private var descriptionSection: some View {
        Group {
            if let description = game.description, !description.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("About")
                        .font(.headline)

                    Text(description.strippingHTML())
                        .font(.body)
                        .foregroundStyle(.secondary)
                }
                .padding(.horizontal)
            }
        }
    }
}

extension String {
    func strippingHTML() -> String {
        self.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
    }
}
