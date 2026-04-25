//
//  PlatformPickerView.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI

struct PlatformPickerView: View {
    let onSelect: (RAWGPlatformDetail) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var platforms: [RAWGPlatformDetail] = []
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var searchText = ""

    private let service = RAWGService()

    private var filteredPlatforms: [RAWGPlatformDetail] {
        if searchText.isEmpty {
            return platforms
        }
        return platforms.filter { platform in
            platform.name.localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        content
            .navigationTitle("Platform")
            .navigationBarTitleDisplayMode(.inline)
            .searchable(text: $searchText, prompt: "Search platforms")
            .task {
                await loadPlatforms()
            }
    }

    @ViewBuilder
    private var content: some View {
        if isLoading && platforms.isEmpty {
            ProgressView("Loading platforms...")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let errorMessage {
            ContentUnavailableView(
                "Couldn't Load Platforms",
                systemImage: "exclamationmark.triangle",
                description: Text(errorMessage)
            )
        } else {
            List(filteredPlatforms) { platform in
                Button {
                    onSelect(platform)
                    dismiss()
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(platform.name)
                                .font(.body)
                                .foregroundStyle(.primary)

                            Text("\(platform.gamesCount) games")
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

    private func loadPlatforms() async {
        guard platforms.isEmpty else { return }

        isLoading = true
        errorMessage = nil

        do {
            let fetched = try await service.getPlatforms()
            platforms = fetched.sorted { left, right in
                left.gamesCount > right.gamesCount
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}
