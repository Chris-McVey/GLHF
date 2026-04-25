//
//  CreateCollectionViewModel.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation
import SwiftData

@Observable
@MainActor
final class CreateCollectionViewModel {
    var name = ""
    var selectedIcon = "folder"

    var platformID: Int?
    var platformName: String?
    var genreID: Int?
    var genreName: String?
    var developerID: Int?
    var developerName: String?
    var searchQuery = ""
    var dateFromYear: Int?
    var dateToYear: Int?

    var previewCount: Int?
    var isLoadingPreview = false
    var previewError: String?

    private let service = RAWGService()
    private var previewTask: Task<Void, Never>?

    var hasFilters: Bool {
        platformID != nil
            || genreID != nil
            || developerID != nil
            || !searchQuery.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            || dateFromYear != nil
            || dateToYear != nil
    }

    var isValid: Bool {
        !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    func clearPlatform() {
        platformID = nil
        platformName = nil
        schedulePreviewRefresh()
    }

    func clearGenre() {
        genreID = nil
        genreName = nil
        schedulePreviewRefresh()
    }

    func clearDeveloper() {
        developerID = nil
        developerName = nil
        schedulePreviewRefresh()
    }

    func selectPlatform(_ platform: RAWGPlatformDetail) {
        platformID = platform.id
        platformName = platform.name
        schedulePreviewRefresh()
    }

    func selectGenre(_ genre: RAWGGenre) {
        genreID = genre.id
        genreName = genre.name
        schedulePreviewRefresh()
    }

    func selectDeveloper(_ developer: RAWGDeveloper) {
        developerID = developer.id
        developerName = developer.name
        schedulePreviewRefresh()
    }

    func schedulePreviewRefresh() {
        previewTask?.cancel()

        guard hasFilters else {
            previewCount = nil
            previewError = nil
            isLoadingPreview = false
            return
        }

        previewTask = Task {
            try? await Task.sleep(for: .milliseconds(500))
            if Task.isCancelled { return }
            await refreshPreview()
        }
    }

    private func refreshPreview() async {
        isLoadingPreview = true
        previewError = nil

        let temp = GameCollection(name: "preview")
        temp.platformID = platformID
        temp.genreID = genreID
        temp.developerID = developerID
        let trimmedSearch = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        temp.searchQuery = trimmedSearch.isEmpty ? nil : trimmedSearch
        temp.dateFromYear = dateFromYear
        temp.dateToYear = dateToYear

        do {
            let count = try await service.countGamesByCollection(temp)
            if Task.isCancelled { return }
            previewCount = count
        } catch {
            if Task.isCancelled { return }
            previewError = error.localizedDescription
            previewCount = nil
        }

        isLoadingPreview = false
    }

    func save(modelContext: ModelContext) {
        let collection = GameCollection(
            name: name.trimmingCharacters(in: .whitespacesAndNewlines),
            icon: selectedIcon
        )
        collection.platformID = platformID
        collection.platformName = platformName
        collection.genreID = genreID
        collection.genreName = genreName
        collection.developerID = developerID
        collection.developerName = developerName

        let trimmedSearch = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        collection.searchQuery = trimmedSearch.isEmpty ? nil : trimmedSearch
        collection.dateFromYear = dateFromYear
        collection.dateToYear = dateToYear

        if let count = previewCount {
            collection.totalCatalogSize = count
            collection.lastSyncedAt = Date()
        }

        modelContext.insert(collection)
    }
}
