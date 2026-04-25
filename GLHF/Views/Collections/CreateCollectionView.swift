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
                nameAndIconSection(vm: viewModel)
                filtersSection(vm: viewModel)
                yearRangeSection(vm: viewModel)
                previewSection
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

    private func nameAndIconSection(@Bindable vm: CreateCollectionViewModel) -> some View {
        Group {
            Section("Collection Name") {
                TextField("e.g. NES Library", text: $vm.name)
            }

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
        } footer: {
            Text("Filters are optional. Leave them blank for a fully manual collection.")
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
