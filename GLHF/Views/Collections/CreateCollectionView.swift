//
//  CreateCollectionView.swift
//  Bounty Board
//
//  Created by Chris McVey on 2/22/26.
//

import SwiftUI
import SwiftData

struct CreateCollectionView: View {
    @Environment(\.modelContext) private var modelContext
    @Environment(\.dismiss) private var dismiss
    @State private var viewModel = CreateCollectionViewModel()

    private let iconOptions = [
        "folder", "gamecontroller", "heart", "star",
        "trophy", "flag", "bookmark", "cart",
        "gift", "crown", "bolt", "flame"
    ]

    var body: some View {
        NavigationStack {
            Form {
                nameSection(vm: viewModel)
                creationModeSection

                if viewModel.creationMode == .canonical {
                    canonicalPresetSection
                }

                iconSection(vm: viewModel)

                if viewModel.creationMode == .smart {
                    filtersSection(vm: viewModel)
                    yearRangeSection(vm: viewModel)
                    previewSection
                }
            }
            .navigationTitle("New Collection")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }

                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        viewModel.save(modelContext: modelContext)
                        dismiss()
                    }
                    .disabled(!viewModel.isValid)
                }
            }
        }
    }

    private func nameSection(@Bindable vm: CreateCollectionViewModel) -> some View {
        Section("Collection Name") {
            TextField("e.g. My NES Library", text: $vm.name)
        }
    }

    private var creationModeSection: some View {
        Section {
            Picker("Start from", selection: $viewModel.creationMode) {
                ForEach(CollectionCreationMode.allCases) { mode in
                    Text(mode.rawValue).tag(mode)
                }
            }
            .pickerStyle(.inline)
            .onChange(of: viewModel.creationMode) {
                viewModel.onCreationModeChanged()
            }
        } footer: {
            switch viewModel.creationMode {
            case .canonical:
                Text("Pick a bundled checklist, then name your collection.")
            case .smart:
                Text("Build a living filter from RAWG. Good for genres or publishers, not a fixed canon.")
            case .manual:
                Text("Add games yourself from Discover.")
            }
        }
    }

    @ViewBuilder
    private var canonicalPresetSection: some View {
        Section {
            if viewModel.canonicalPresets.isEmpty {
                Label("Canonical list file missing from app bundle.", systemImage: "exclamationmark.triangle")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(viewModel.canonicalPresets) { preset in
                    Button {
                        viewModel.selectPreset(preset)
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(preset.displayName)
                                    .font(.headline)
                                    .foregroundStyle(.primary)
                                Text("\(preset.gameCount) games · \(preset.platformName)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if viewModel.selectedPreset?.id == preset.id {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.tint)
                            }
                        }
                    }
                }

                if let preset = viewModel.selectedPreset {
                    Text(preset.attribution)
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if let urlString = preset.wikipediaListUrl, let url = URL(string: urlString) {
                        Link("View Wikipedia source list", destination: url)
                            .font(.caption)
                    }
                }
            }
        } header: {
            Text("Library checklist")
        } footer: {
            Text("Wikipedia-based lists (licensed and unlicensed Western retail).")
        }
    }

    private func iconSection(@Bindable vm: CreateCollectionViewModel) -> some View {
        Section("Icon") {
            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 6), spacing: 16) {
                ForEach(iconOptions, id: \.self) { icon in
                    Image(systemName: icon)
                        .font(.title2)
                        .frame(width: 44, height: 44)
                        .background(
                            viewModel.selectedIcon == icon
                                ? Color.accentColor.opacity(0.2)
                                : Color.clear
                        )
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .onTapGesture {
                            viewModel.selectedIcon = icon
                        }
                }
            }
            .padding(.vertical, 8)
        }
    }

    private func filtersSection(@Bindable vm: CreateCollectionViewModel) -> some View {
        Section {
            filterRow(
                title: "Platform",
                value: viewModel.platformName,
                clear: viewModel.clearPlatform
            ) {
                PlatformPickerView { platform in
                    viewModel.selectPlatform(platform)
                }
            }

            filterRow(
                title: "Genre",
                value: viewModel.genreName,
                clear: viewModel.clearGenre
            ) {
                GenrePickerView { genre in
                    viewModel.selectGenre(genre)
                }
            }

            filterRow(
                title: "Developer",
                value: viewModel.developerName,
                clear: viewModel.clearDeveloper
            ) {
                DeveloperPickerView { developer in
                    viewModel.selectDeveloper(developer)
                }
            }

            HStack {
                Text("Title contains")
                Spacer()
                TextField("optional", text: $vm.searchQuery)
                    .multilineTextAlignment(.trailing)
                    .textInputAutocapitalization(.never)
                    .onChange(of: vm.searchQuery) {
                        viewModel.schedulePreviewRefresh()
                    }
            }
        } header: {
            Text("Filters")
        }
    }

    private func yearRangeSection(@Bindable vm: CreateCollectionViewModel) -> some View {
        Section("Release Year") {
            HStack {
                Text("From")
                Spacer()
                TextField("any", value: $vm.dateFromYear, format: .number.grouping(.never))
                    .multilineTextAlignment(.trailing)
                    .keyboardType(.numberPad)
                    .frame(width: 80)
                    .onChange(of: vm.dateFromYear) {
                        viewModel.schedulePreviewRefresh()
                    }
            }

            HStack {
                Text("To")
                Spacer()
                TextField("any", value: $vm.dateToYear, format: .number.grouping(.never))
                    .multilineTextAlignment(.trailing)
                    .keyboardType(.numberPad)
                    .frame(width: 80)
                    .onChange(of: vm.dateToYear) {
                        viewModel.schedulePreviewRefresh()
                    }
            }
        }
    }

    @ViewBuilder
    private var previewSection: some View {
        if viewModel.hasFilters {
            Section("Preview") {
                if viewModel.isLoadingPreview {
                    HStack {
                        ProgressView()
                            .scaleEffect(0.8)
                        Text("Counting matching games...")
                            .foregroundStyle(.secondary)
                    }
                } else if let error = viewModel.previewError {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .foregroundStyle(.red)
                        .font(.caption)
                } else if let count = viewModel.previewCount {
                    HStack {
                        Image(systemName: "gamecontroller.fill")
                            .foregroundStyle(.tint)
                        Text("\(count) games match")
                            .font(.headline)
                        Spacer()
                    }
                }
            }
        }
    }

    private func filterRow<Destination: View>(
        title: String,
        value: String?,
        clear: @escaping () -> Void,
        @ViewBuilder destination: @escaping () -> Destination
    ) -> some View {
        HStack {
            NavigationLink {
                destination()
            } label: {
                HStack {
                    Text(title)
                    Spacer()
                    Text(value ?? "Any")
                        .foregroundStyle(.secondary)
                }
            }

            if value != nil {
                Button {
                    clear()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }
        }
    }
}

#Preview {
    CreateCollectionView()
        .modelContainer(for: GameCollection.self, inMemory: true)
}
