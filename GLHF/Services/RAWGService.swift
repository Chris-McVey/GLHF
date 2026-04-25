//
//  RAWGService.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation

@Observable
final class RAWGService {
    private let apiKey = Secrets.rawgAPIKey
    private let baseURL = "https://api.rawg.io/api"

    func searchGames(query: String) async throws -> [RAWGGame] {
        let queryItems = [
            URLQueryItem(name: "search", value: query),
            URLQueryItem(name: "page_size", value: "20")
        ]
        let response: RAWGPaginatedResponse<RAWGGame> = try await get(path: "/games", queryItems: queryItems)
        return response.results
    }

    func getGameDetail(id: Int) async throws -> RAWGGame {
        try await get(path: "/games/\(id)", queryItems: [])
    }

    func getPlatforms() async throws -> [RAWGPlatformDetail] {
        var allPlatforms: [RAWGPlatformDetail] = []
        var page = 1
        let pageSize = 40

        while true {
            let queryItems = [
                URLQueryItem(name: "page", value: "\(page)"),
                URLQueryItem(name: "page_size", value: "\(pageSize)")
            ]
            let response: RAWGPaginatedResponse<RAWGPlatformDetail> = try await get(path: "/platforms", queryItems: queryItems)
            allPlatforms.append(contentsOf: response.results)

            if response.next == nil { break }
            page += 1
        }

        return allPlatforms
    }

    func getGenres() async throws -> [RAWGGenre] {
        let response: RAWGPaginatedResponse<RAWGGenre> = try await get(path: "/genres", queryItems: [])
        return response.results
    }

    func searchDevelopers(query: String) async throws -> [RAWGDeveloper] {
        let queryItems = [
            URLQueryItem(name: "search", value: query),
            URLQueryItem(name: "page_size", value: "20")
        ]
        let response: RAWGPaginatedResponse<RAWGDeveloper> = try await get(path: "/developers", queryItems: queryItems)
        return response.results
    }

    func getGamesByCollection(_ collection: GameCollection, page: Int = 1, pageSize: Int = 20) async throws -> RAWGPaginatedResponse<RAWGGame> {
        var queryItems = collectionFilterQueryItems(collection)
        queryItems.append(URLQueryItem(name: "page", value: "\(page)"))
        queryItems.append(URLQueryItem(name: "page_size", value: "\(pageSize)"))
        return try await get(path: "/games", queryItems: queryItems)
    }

    func countGamesByCollection(_ collection: GameCollection) async throws -> Int {
        var queryItems = collectionFilterQueryItems(collection)
        queryItems.append(URLQueryItem(name: "page_size", value: "1"))
        let response: RAWGPaginatedResponse<RAWGGame> = try await get(path: "/games", queryItems: queryItems)
        return response.count
    }

    func getGames(byIds ids: [Int]) async throws -> [RAWGGame] {
        guard !ids.isEmpty else { return [] }

        return try await withThrowingTaskGroup(of: RAWGGame.self) { group in
            for id in ids {
                group.addTask {
                    try await self.getGameDetail(id: id)
                }
            }

            var games: [RAWGGame] = []
            for try await game in group {
                games.append(game)
            }
            return games
        }
    }

    private func collectionFilterQueryItems(_ collection: GameCollection) -> [URLQueryItem] {
        var items: [URLQueryItem] = []

        if let platformID = collection.platformID {
            items.append(URLQueryItem(name: "platforms", value: "\(platformID)"))
        }
        if let genreID = collection.genreID {
            items.append(URLQueryItem(name: "genres", value: "\(genreID)"))
        }
        if let developerID = collection.developerID {
            items.append(URLQueryItem(name: "developers", value: "\(developerID)"))
        }
        if let searchQuery = collection.searchQuery, !searchQuery.isEmpty {
            items.append(URLQueryItem(name: "search", value: searchQuery))
            items.append(URLQueryItem(name: "search_precise", value: "true"))
        }
        if collection.dateFromYear != nil || collection.dateToYear != nil {
            let from = collection.dateFromYear.map { "\($0)-01-01" } ?? "1970-01-01"
            let to = collection.dateToYear.map { "\($0)-12-31" } ?? "2100-12-31"
            items.append(URLQueryItem(name: "dates", value: "\(from),\(to)"))
        }

        if !collection.excludedAPIIds.isEmpty {
            let excluded = collection.excludedAPIIds.map(String.init).joined(separator: ",")
            items.append(URLQueryItem(name: "exclude_additions", value: excluded))
        }

        return items
    }

    private func get<T: Decodable>(path: String, queryItems: [URLQueryItem]) async throws -> T {
        var components = URLComponents(string: baseURL + path)
        var allItems = queryItems
        allItems.append(URLQueryItem(name: "key", value: apiKey))
        components?.queryItems = allItems

        guard let url = components?.url else {
            throw RAWGError.invalidURL
        }

        let (data, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw RAWGError.invalidResponse
        }

        let decoder = JSONDecoder()
        return try decoder.decode(T.self, from: data)
    }
}

enum RAWGError: LocalizedError {
    case invalidURL
    case invalidResponse
    case decodingFailed

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The URL was invalid."
        case .invalidResponse:
            return "The server returned an unexpected response."
        case .decodingFailed:
            return "Failed to read the game data."
        }
    }
}
