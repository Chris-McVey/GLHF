//
//  Game.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation
import SwiftData

@Model
final class Game {
    @Attribute(.unique) var apiId: Int
    var title: String
    var coverImageURL: String?
    var summary: String?
    var platforms: String?
    var releaseDate: Date?
    var genres: String?

    @Relationship(deleteRule: .cascade, inverse: \Review.game)
    var reviews: [Review] = []

    @Relationship(deleteRule: .cascade, inverse: \CollectionEntry.game)
    var collectionEntries: [CollectionEntry] = []

    init(
        apiId: Int,
        title: String,
        coverImageURL: String? = nil,
        summary: String? = nil,
        platforms: String? = nil,
        releaseDate: Date? = nil,
        genres: String? = nil
    ) {
        self.apiId = apiId
        self.title = title
        self.coverImageURL = coverImageURL
        self.summary = summary
        self.platforms = platforms
        self.releaseDate = releaseDate
        self.genres = genres
    }
}
