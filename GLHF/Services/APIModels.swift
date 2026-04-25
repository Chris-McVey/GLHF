//
//  APIModels.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation

struct RAWGPaginatedResponse<Item: Codable>: Codable {
    let count: Int
    let next: String?
    let previous: String?
    let results: [Item]
}

struct RAWGGame: Codable, Identifiable {
    let id: Int
    let name: String
    let released: String?
    let backgroundImage: String?
    let rating: Double?
    let genres: [RAWGGenre]?
    let platforms: [RAWGPlatformWrapper]?
    let description: String?

    enum CodingKeys: String, CodingKey {
        case id, name, released, rating, genres, platforms, description
        case backgroundImage = "background_image"
    }

    var genreNames: String {
        guard let genres else { return "" }
        return genres.map { genre in genre.name }.joined(separator: ", ")
    }

    var platformNames: String {
        guard let platforms else { return "" }
        return platforms.map { wrapper in wrapper.platform.name }.joined(separator: ", ")
    }

    var releaseDate: Date? {
        guard let released else { return nil }
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.date(from: released)
    }
}

struct RAWGGenre: Codable, Identifiable {
    let id: Int
    let name: String
    let slug: String?
    let gamesCount: Int?

    enum CodingKeys: String, CodingKey {
        case id, name, slug
        case gamesCount = "games_count"
    }
}

struct RAWGPlatformWrapper: Codable {
    let platform: RAWGPlatform
}

struct RAWGPlatform: Codable {
    let id: Int
    let name: String
}

struct RAWGPlatformDetail: Codable, Identifiable {
    let id: Int
    let name: String
    let slug: String
    let gamesCount: Int
    let yearStart: Int?
    let yearEnd: Int?
    let imageBackground: String?

    enum CodingKeys: String, CodingKey {
        case id, name, slug
        case gamesCount = "games_count"
        case yearStart = "year_start"
        case yearEnd = "year_end"
        case imageBackground = "image_background"
    }
}

struct RAWGDeveloper: Codable, Identifiable {
    let id: Int
    let name: String
    let slug: String
    let gamesCount: Int
    let imageBackground: String?

    enum CodingKeys: String, CodingKey {
        case id, name, slug
        case gamesCount = "games_count"
        case imageBackground = "image_background"
    }
}
