import SwiftUI

struct SearchView: View {
    @EnvironmentObject private var radar: RadarService
    @EnvironmentObject private var watchlist: WatchlistStore
    @EnvironmentObject private var purchases: PurchaseStore
    @EnvironmentObject private var journal: DecisionJournal
    @State private var ticker = ""
    @State private var showPaywall = false
    @State private var paywallTicker: String?
    @State private var gateMessage: String?
    @State private var chaseCheck = ChaseCheck()
    @State private var decisionSaved = false
    @State private var planVerdict: RadarVerdict?
    @FocusState private var focused: Bool

    private var lockedPreview: Bool {
        guard let verdict = radar.latest else { return false }
        return AppAccess.isPreviewLocked(ticker: verdict.ticker, unlocked: purchases.effectiveUnlocked)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text(AppAccess.differentiationLine)
                        .font(.footnote)
                        .foregroundStyle(QRTheme.muted)

                    HStack {
                        TextField("Ticker (e.g. AAPL)", text: $ticker)
                            .textInputAutocapitalization(.characters)
                            .autocorrectionDisabled()
                            .focused($focused)
                            .accessibilityIdentifier("tickerField")
                            .padding(14)
                            .background(QRTheme.panel)
                            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                            .foregroundStyle(QRTheme.text)

                        Button("Scan") { Task { await runScan() } }
                            .buttonStyle(.borderedProminent)
                            .tint(QRTheme.radar)
                            .foregroundStyle(.black)
                            .disabled(radar.isLoading || ticker.trimmingCharacters(in: .whitespaces).isEmpty)
                            .accessibilityIdentifier("runScanButton")
                    }

                    HStack(spacing: 8) {
                        ForEach(["SPY", "AAPL", "NVDA", "MSFT"], id: \.self) { chip in
                            Button(chip) {
                                ticker = chip
                                Task { await runScan() }
                            }
                            .font(.caption.weight(.semibold))
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(QRTheme.radarDim)
                            .foregroundStyle(QRTheme.radar)
                            .clipShape(Capsule())
                        }
                    }

                    ChaseCheckView(
                        check: $chaseCheck,
                        ticker: AppAccess.normalizeTicker(ticker)
                    )

                    if !purchases.effectiveUnlocked {
                        Text(previewCaption)
                            .font(.caption)
                            .foregroundStyle(QRTheme.muted)
                    }

                    if radar.isLoading {
                        ProgressView("Running mechanical scan…")
                            .tint(QRTheme.radar)
                            .foregroundStyle(QRTheme.muted)
                    }

                    if let gateMessage {
                        Text(gateMessage)
                            .font(.footnote)
                            .foregroundStyle(QRTheme.warn)
                    }

                    if let err = radar.errorMessage {
                        Text(err)
                            .font(.footnote)
                            .foregroundStyle(QRTheme.warn)
                    }

                    if let v = radar.latest {
                        if lockedPreview {
                            LockedVerdictView(verdict: v) {
                                paywallTicker = v.ticker
                                showPaywall = true
                            }
                        } else {
                            VerdictCardView(verdict: v)
                            DecisionCommitView(
                                verdict: v,
                                chaseCheck: chaseCheck,
                                isSaved: decisionSaved
                            ) {
                                journal.record(verdict: v, chaseCheck: chaseCheck)
                                decisionSaved = true
                            }
                            Button { planVerdict = v } label: {
                                Label("Write conditions & set a review date", systemImage: "square.and.pencil")
                            }
                            .buttonStyle(.bordered)
                            Text("Educational only — not investment advice. Not a broker.")
                                .font(.caption2)
                                .foregroundStyle(QRTheme.muted)
                            Button {
                                addToWatch(v.ticker)
                            } label: {
                                Label("Add to Watch", systemImage: "eye")
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                }
                .padding(20)
                .frame(maxWidth: 760)
                .frame(maxWidth: .infinity)
            }
            .background(QRTheme.bg.ignoresSafeArea())
            .navigationTitle("Scan")
            .onChange(of: ticker) { _, _ in
                #if DEBUG
                if ScreenshotLaunch.isEnabled { return }
                #endif
                chaseCheck.reset()
                decisionSaved = false
            }
            .onChange(of: radar.latest?.ticker) { _, _ in
                if let v = radar.latest, !lockedPreview { ReviewPrompt.recordVerdict(v) }
            }
            .onChange(of: purchases.effectiveUnlocked) { _, unlocked in
                guard unlocked else { gateMessage = nil; return }
                gateMessage = "Unlocked. The \(paywallTicker ?? "requested") posture is now visible."
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView(focusTicker: paywallTicker)
                    .environmentObject(purchases)
            }
            .sheet(item: $planVerdict) { verdict in
                NavigationStack { DecisionPlanComposer(verdict: verdict) }.tint(QRTheme.radar)
            }
            .task {
                #if DEBUG
                await prepareScreenshotScanIfNeeded()
                #endif
            }
        }
    }

    #if DEBUG
    private func prepareScreenshotScanIfNeeded() async {
        guard ScreenshotLaunch.isEnabled else { return }
        switch ScreenshotLaunch.screen {
        case "scan", "decision":
            AppAccess.storage.set("AAPL", forKey: AppAccess.previewTickerKey)
            ticker = "AAPL"
            chaseCheck.entryWasPlanned = true
            chaseCheck.invalidationIsDefined = true
            chaseCheck.independentOfHype = true
            await runScan()
            if ScreenshotLaunch.screen == "decision", let v = radar.latest, !lockedPreview {
                journal.record(verdict: v, chaseCheck: chaseCheck)
                decisionSaved = true
            }
        case "paywall":
            AppAccess.storage.set("AAPL", forKey: AppAccess.previewTickerKey)
            ticker = "NVDA"
            await runScan()
        default:
            break
        }
    }
    #endif

    private var previewCaption: String {
        if let claimed = AppAccess.claimedPreviewTicker {
            return "Free ticker: \(claimed). Unlock for any other symbol."
        }
        return AppAccess.previewLine
    }

    private func runScan() async {
        focused = false
        gateMessage = nil
        decisionSaved = false
        let symbol = AppAccess.normalizeTicker(ticker)
        let ok = await radar.analyze(ticker: symbol)
        guard ok, let latest = radar.latest else { return }
        if AppAccess.isPreviewLocked(ticker: latest.ticker, unlocked: purchases.effectiveUnlocked) {
            paywallTicker = symbol
            showPaywall = true
            return
        }
        if !latest.isWithheld {
            AppAccess.claimPreviewTickerIfNeeded(symbol, withheld: false)
            DisciplineLedger.record(action: latest.actionCode, ticker: symbol, close: nil)
        }
    }

    private func addToWatch(_ ticker: String) {
        guard purchases.effectiveUnlocked else {
            gateMessage = "Unlock to use Watch."
            paywallTicker = ticker
            showPaywall = true
            return
        }
        if !watchlist.add(ticker: ticker, limit: purchases.watchlistLimit) {
            gateMessage = "Watchlist full (\(purchases.watchlistLimit))."
        }
    }
}
