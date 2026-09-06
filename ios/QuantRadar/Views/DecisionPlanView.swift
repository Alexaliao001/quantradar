import SwiftUI

struct DecisionPlanComposer: View {
    @EnvironmentObject private var journal: DecisionJournal
    @Environment(\.dismiss) private var dismiss
    let verdict: RadarVerdict?
    @State private var ticker: String
    @State private var reason = ""
    @State private var trigger = ""
    @State private var invalidation = ""
    @State private var reviewOn = Date()
    @State private var decision = "WAIT"
    @State private var error: String?
    @FocusState private var fieldFocused: Bool

    init(verdict: RadarVerdict? = nil) {
        self.verdict = verdict
        _ticker = State(initialValue: verdict?.ticker ?? "")
    }

    var body: some View {
        Form {
            Section {
                Text("Write the conditions before you know the outcome. Saving keeps this original plan unchanged; your review will be added separately.")
                    .font(.subheadline)
                    .foregroundStyle(QRTheme.muted)
            }
            Section("Your decision") {
                TextField("Ticker", text: $ticker)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                    .disabled(verdict != nil)
                    .accessibilityIdentifier("planTicker")
                    .focused($fieldFocused)
                Picker("My decision", selection: $decision) {
                    ForEach(["PAUSE", "WAIT", "PASS", "REVIEW"], id: \.self) { Text($0).tag($0) }
                }
                Text("Your choice, not a recommendation to buy or sell.")
                    .font(.caption)
                    .foregroundStyle(QRTheme.muted)
            }
            Section("1 · Why am I considering it?") {
                TextField("My reason, in my own words", text: $reason, axis: .vertical)
                    .lineLimit(2...5)
                    .accessibilityIdentifier("planReason")
                    .focused($fieldFocused)
            }
            Section("2 · What must happen first?") {
                TextField("The condition I will wait for", text: $trigger, axis: .vertical)
                    .lineLimit(2...5)
                    .accessibilityIdentifier("planTrigger")
                    .focused($fieldFocused)
            }
            Section("3 · What would change my mind?") {
                TextField("What invalidates this idea", text: $invalidation, axis: .vertical)
                    .lineLimit(2...5)
                    .accessibilityIdentifier("planInvalidation")
                    .focused($fieldFocused)
            }
            Section {
                DatePicker("Review on", selection: $reviewOn,
                           in: Calendar.current.startOfDay(for: Date())..., displayedComponents: .date)
                Text("The date appears in your review queue. It does not schedule a notification or place a trade.")
                    .font(.caption)
                    .foregroundStyle(QRTheme.muted)
                if let verdict {
                    Text("Radar snapshot: \(verdict.isWithheld ? "UNKNOWN" : verdict.actionCode) · \(verdict.meta?.marketAsOf ?? "session not recorded")")
                        .font(.caption)
                } else {
                    Text("No market data is needed. This is your own written plan.")
                        .font(.caption)
                }
            }
            if let error { Section { Text(error).foregroundStyle(QRTheme.warn) } }
        }
        .scrollContentBackground(.hidden)
        .scrollDismissesKeyboard(.interactively)
        .background(QRTheme.bg)
        .navigationTitle("Write a decision")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { fieldFocused = false }
                    .accessibilityIdentifier("dismissPlanKeyboard")
            }
            ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
            ToolbarItem(placement: .confirmationAction) {
                Button("Save plan") { save() }
                    .fontWeight(.semibold)
                    .disabled([ticker, reason, trigger, invalidation].contains { $0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty })
                    .accessibilityIdentifier("saveDecisionPlan")
            }
        }
    }

    private func save() {
        do {
            try journal.commitPlan(ticker: ticker, reason: reason, trigger: trigger,
                                   invalidation: invalidation, reviewOn: reviewOn,
                                   decision: decision, verdict: verdict)
            dismiss()
        } catch { self.error = error.localizedDescription }
    }
}

struct DecisionDetailView: View {
    @EnvironmentObject private var journal: DecisionJournal
    let entryID: UUID
    @State private var outcome: DecisionReview.Outcome = .didNotAct
    @State private var lesson = ""
    @State private var error: String?
    @FocusState private var reviewFocused: Bool

    private var entry: DecisionEntry? { journal.entries.first { $0.id == entryID } }

    var body: some View {
        Form {
            if let entry {
                Section {
                    Label("Original record preserved", systemImage: "lock.doc")
                        .foregroundStyle(QRTheme.radar)
                    Text(entry.createdAt.formatted(date: .abbreviated, time: .shortened))
                        .font(.caption)
                    LabeledContent("My decision", value: entry.decision)
                    if entry.radarAction != "NOT SCANNED" {
                        LabeledContent("Radar then", value: entry.radarAction)
                        Text("Market session: \(entry.marketAsOf ?? "Not recorded")")
                            .font(.caption)
                    }
                }
                if let plan = entry.plan {
                    Section("Before · My original plan") {
                        original("My reason", plan.reason)
                        original("Condition to observe", plan.trigger)
                        original("What invalidates it", plan.invalidation)
                        LabeledContent("Review date", value: plan.reviewOn.formatted(date: .abbreviated, time: .omitted))
                    }
                } else {
                    Section { Text("This quick log has no written conditions attached. Its original decision is preserved.").font(.caption) }
                }
                if let review = entry.review {
                    Section("After · My process review") {
                        Text(review.outcome.rawValue).font(.headline)
                            .accessibilityIdentifier("savedReviewOutcome")
                        Text(review.lesson)
                        Text(review.reviewedAt.formatted(date: .abbreviated, time: .shortened))
                            .font(.caption)
                            .foregroundStyle(QRTheme.muted)
                    }
                } else {
                    Section("After · Review the process") {
                        Text("Compare what you did with what you wrote. A good price outcome does not prove a good process.")
                            .font(.caption)
                            .foregroundStyle(QRTheme.muted)
                        Picker("What did I do?", selection: $outcome) {
                            ForEach(DecisionReview.Outcome.allCases, id: \.self) { Text($0.rawValue).tag($0) }
                        }
                        TextField("What will I repeat or change next time?", text: $lesson, axis: .vertical)
                            .lineLimit(3...6)
                            .accessibilityIdentifier("reviewLesson")
                            .focused($reviewFocused)
                        Button("Save review") {
                            do { try journal.completeReview(id: entryID, outcome: outcome, lesson: lesson) }
                            catch { self.error = error.localizedDescription }
                        }
                        .disabled(lesson.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        .accessibilityIdentifier("saveDecisionReview")
                        Text("Saving adds one dated review without rewriting the original plan.")
                            .font(.caption)
                            .foregroundStyle(QRTheme.muted)
                    }
                }
                if let error { Section { Text(error).foregroundStyle(QRTheme.warn) } }
                Section {
                    ShareLink(item: entry.exportText) { Label("Share this record", systemImage: "square.and.arrow.up") }
                        .accessibilityIdentifier("shareDecisionRecord")
                    Text("Only share with people you choose. These are your notes, not verified trades or returns.")
                        .font(.caption)
                        .foregroundStyle(QRTheme.muted)
                }
            } else {
                Text("This record is no longer in your journal.")
            }
        }
        .scrollContentBackground(.hidden)
        .scrollDismissesKeyboard(.interactively)
        .background(QRTheme.bg)
        .navigationTitle(entry?.ticker ?? "Decision")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { reviewFocused = false }
                    .accessibilityIdentifier("dismissPlanKeyboard")
            }
        }
    }

    private func original(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title).font(.caption).foregroundStyle(QRTheme.muted)
            Text(value).foregroundStyle(QRTheme.text).textSelection(.enabled)
        }
        .padding(.vertical, 4)
    }
}
