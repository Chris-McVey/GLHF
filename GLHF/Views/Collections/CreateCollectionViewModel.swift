//
//  CreateCollectionViewModel.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import Foundation
import SwiftData

enum CollectionCreationMode: String, CaseIterable, Identifiable {
    case canonical = "Complete library"
    case smart = "Smart filter"
    case manual = "Empty collection"

    var id: String { rawValue }
}

@Observable
@MainActor
final class CreateCollectionViewModel {
    var creationMode: CollectionCreationMode = .canonical
    var selectedPresetID: String?
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

    let canonicalPresets = CanonicalSetService.availablePresets()

    private let service = RAWGService()
    private var previewTask: Task<Void, Never>?

    var selectedPreset: CanonicalSetPreset? {
        guard let selectedPresetID else { return canonicalPresets.first }
        return canonicalPresets.first { $0.id == selectedPresetID }
            ?? canonicalPresets.first
    }

    var hasFilters: Bool {
        guard creationMode == .smart else { return false }
        return platformID != nil
            || genreID != nil
            || developerID != nil
            || !searchQuery.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            || dateFromYear != nil
            || dateToYear != nil
    }

    var isValid: Bool {
        let trimmedName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        switch creationMode {
        case .canonical:
            return selectedPreset != nil && !trimmedName.isEmpty
        case .smart, .manual:
            return !trimmedName.isEmpty
        }
    }

    init() {
        if let first = canonicalPresets.first {
            selectedPresetID = first.id
        }
    }

    func selectPreset(_ preset: CanonicalSetPreset) {
        selectedPresetID = preset.id
        applyPresetMetadata(preset)
    }

    private func applyPresetMetadata(_ preset: CanonicalSetPreset) {
        platformID = CanonicalGameID.nesRAWGPlatformID
        platformName = preset.platformName
    }

    func onCreationModeChanged() {
        previewTask?.cancel()
        previewCount = nil
        previewError = nil
        isLoadingPreview = false

        switch creationMode {
        case .canonical:
            if selectedPresetID == nil, let first = canonicalPresets.first {
                selectedPresetID = first.id
            }
            if let preset = selectedPreset {
                applyPresetMetadata(preset)
            }
            selectedIcon = "gamecontroller"
        case .smart:
            schedulePreviewRefresh()
        case .manual:
            platformID = nil
            platformName = nil
            genreID = nil
            genreName = nil
            developerID = nil
            developerName = nil
            searchQuery = ""
            dateFromYear = nil
            dateToYear = nil
        }
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

        guard creationMode == .smart, hasFilters else {
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
        let trimmedName = name.trimmingCharacters(in: .whitespacesAndNewlines)

        switch creationMode {
        case .canonical:
            saveCanonicalCollection(name: trimmedName, modelContext: modelContext)
        case .smart:
            saveSmartCollection(name: trimmedName, modelContext: modelContext)
        case .manual:
            saveManualCollection(name: trimmedName, modelContext: modelContext)
        }
    }

    private func saveCanonicalCollection(name: String, modelContext: ModelContext) {
        guard let preset = selectedPreset else { return }

        let collection = GameCollection(name: name, icon: selectedIcon)
        collection.canonicalSetID = preset.id
        collection.canonicalSetVersion = preset.version
        collection.totalCatalogSize = preset.gameCount
        collection.platformID = CanonicalGameID.nesRAWGPlatformID
        collection.platformName = preset.platformName
        collection.lastSyncedAt = Date()
        modelContext.insert(collection)
    }

    private func saveSmartCollection(name: String, modelContext: ModelContext) {
        let collection = GameCollection(name: name, icon: selectedIcon)
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

    private func saveManualCollection(name: String, modelContext: ModelContext) {
        let collection = GameCollection(name: name, icon: selectedIcon)
        modelContext.insert(collection)
    }
}
