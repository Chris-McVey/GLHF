//
//  ContentView.swift
//  GLHF
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct ContentView: View {
    var body: some View {
        TabView {
            Tab("Discover", systemImage: "magnifyingglass") {
                DiscoverView()
            }

            Tab("Reviews", systemImage: "star.bubble") {
                ReviewsListView()
            }

            Tab("Collections", systemImage: "square.stack.3d.up") {
                CollectionsListView()
            }
        }
    }
}

#Preview {
    ContentView()
        .modelContainer(
            for: [Game.self, Review.self, GameCollection.self, CollectionEntry.self],
            inMemory: true
        )
}
