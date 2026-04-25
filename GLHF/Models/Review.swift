//
//  Review.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation
import SwiftData

@Model
final class Review {
    var rating: Int
    var title: String
    var body: String
    var createdAt: Date

    var game: Game?

    init(rating: Int, title: String, body: String, game: Game? = nil) {
        self.rating = rating
        self.title = title
        self.body = body
        self.createdAt = Date()
        self.game = game
    }
}
