//
//  ReviewsListView.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct ReviewsListView: View {
    @Query(sort: \Review.createdAt, order: .reverse) private var reviews: [Review]
    @Environment(\.modelContext) private var modelContext

    var body: some View {
        NavigationStack {
            Group {
                if reviews.isEmpty {
                    ContentUnavailableView(
                        "No Reviews Yet",
                        systemImage: "star.bubble",
                        description: Text("Your game reviews will appear here")
                    )
                } else {
                    List {
                        ForEach(reviews) { review in
                            NavigationLink(destination: ReviewDetailView(review: review)) {
                                reviewRow(review)
                            }
                        }
                        .onDelete(perform: deleteReviews)
                    }
                }
            }
            .navigationTitle("My Reviews")
        }
    }

    private func reviewRow(_ review: Review) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if let game = review.game {
                Text(game.title)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text(review.title)
                .font(.headline)

            StarRatingView(
                rating: .constant(review.rating),
                size: .caption,
                interactive: false
            )

            Text(review.createdAt, format: .dateTime.month(.abbreviated).day().year())
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 4)
    }

    private func deleteReviews(offsets: IndexSet) {
        for index in offsets {
            modelContext.delete(reviews[index])
        }
    }
}

#Preview {
    ReviewsListView()
        .modelContainer(
            for: [Game.self, Review.self],
            inMemory: true
        )
}
