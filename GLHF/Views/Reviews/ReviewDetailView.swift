//
//  ReviewDetailView.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI

struct ReviewDetailView: View {
    let review: Review

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let game = review.game {
                    Text(game.title)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                StarRatingView(
                    rating: .constant(review.rating),
                    interactive: false
                )

                Text(review.title)
                    .font(.title2)
                    .fontWeight(.bold)

                if !review.body.isEmpty {
                    Text(review.body)
                        .font(.body)
                }

                Text(review.createdAt, format: .dateTime.month(.wide).day().year())
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationTitle("Review")
        .navigationBarTitleDisplayMode(.inline)
    }
}
