//
//  StarRatingView.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI

struct StarRatingView: View {
    @Binding var rating: Int
    var maxRating = 5
    var size: Font = .title2
    var interactive = true

    var body: some View {
        HStack(spacing: 4) {
            ForEach(1...maxRating, id: \.self) { star in
                Image(systemName: star <= rating ? "star.fill" : "star")
                    .font(size)
                    .foregroundStyle(star <= rating ? .yellow : .gray.opacity(0.4))
                    .onTapGesture {
                        if interactive {
                            rating = star
                        }
                    }
            }
        }
    }
}

#Preview {
    @Previewable @State var rating = 3
    StarRatingView(rating: $rating)
}
