//
//  CanonicalSetService.swift
//  GLHF
//

import Foundation

enum CanonicalSetService {
    private static let bundleFilenames = ["nes": "nes"]

    static func availablePresets() -> [CanonicalSetPreset] {
        bundleFilenames.compactMap { slug, filename in
            guard let bundle = loadBundle(filename: filename) else { return nil }
            return preset(from: bundle)
        }
    }

    static func loadBundle(for collection: GameCollection) -> CanonicalSetBundle? {
        guard let setID = collection.canonicalSetID else { return nil }
        let slug = setID.split(separator: "-").first.map(String.init) ?? "nes"
        guard let filename = bundleFilenames[slug] else { return nil }
        return loadBundle(filename: filename)
    }

    static func catalogGames(for collection: GameCollection) -> [CanonicalBundleGame] {
        loadBundle(for: collection)?.games ?? []
    }

    private static func loadBundle(filename: String) -> CanonicalSetBundle? {
        // Xcode may preserve `Resources/CanonicalSets/` or flatten to the app root.
        let subdirectories: [String?] = ["CanonicalSets", nil]
        for subdirectory in subdirectories {
            guard let url = Bundle.main.url(
                forResource: filename,
                withExtension: "json",
                subdirectory: subdirectory
            ) else {
                continue
            }
            do {
                let data = try Data(contentsOf: url)
                return try JSONDecoder().decode(CanonicalSetBundle.self, from: data)
            } catch {
                continue
            }
        }
        return nil
    }

    private static func preset(from bundle: CanonicalSetBundle) -> CanonicalSetPreset {
        CanonicalSetPreset(
            id: bundle.id,
            version: bundle.version,
            displayName: bundle.displayName,
            platformName: bundle.platformName,
            gameCount: bundle.gameCount,
            primarySource: bundle.primarySource,
            wikipediaListUrl: bundle.wikipediaListUrl,
            attribution: "Game list sourced from Wikipedia (CC BY-SA 3.0)."
        )
    }
}
