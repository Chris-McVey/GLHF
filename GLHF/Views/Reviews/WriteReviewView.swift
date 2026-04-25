//
//  WriteReviewView.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct WriteReviewView: View {
    let game: RAWGGame
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss

    @State private var rating = 3
    @State private var title = ""
    @State private var reviewBody = ""

    private var isValid: Bool {
        !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && rating > 0
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Spacer()
                        StarRatingView(rating: $rating)
                        Spacer()
                    }
                    .padding(.vertical, 8)
                }

                Section("Review Title") {
                    TextField("Give your review a title", text: $title)
                }

                Section("Your Thoughts") {
                    TextEditor(text: $reviewBody)
                        .frame(minHeight: 150)
                }
            }
            .navigationTitle("Review \(game.name)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        saveReview()
                    }
                    .disabled(!isValid)
                }
            }
        }
    }

    private func saveReview() {
        let cachedGame = GameCache.findOrCreate(from: game, in: modelContext)

        let review = Review(
            rating: rating,
            title: title.trimmingCharacters(in: .whitespacesAndNewlines),
            body: reviewBody.trimmingCharacters(in: .whitespacesAndNewlines),
            game: cachedGame
        )

        modelContext.insert(review)
        dismiss()
    }
}
