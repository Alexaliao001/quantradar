import SwiftUI

struct OnboardingView: View {
    @Binding var hasSeenOnboarding: Bool
    @State private var page = 0

    private let pages: [(title: String, body: String)] = [
        ("One score. One action.", "Mechanical posture for US tickers — not a tipster feed."),
        ("Most days: don’t act.", "WAIT and NO are features. The radar earns its keep by skipping bad setups."),
        ("You already paid.", "This is a paid App Store app. Full radar is unlocked — no freemium bait."),
    ]

    var body: some View {
        ZStack {
            QRTheme.bg.ignoresSafeArea()
            VStack(spacing: 28) {
                Spacer()
                Image(systemName: "dot.radiowaves.left.and.right")
                    .font(.system(size: 56, weight: .light))
                    .foregroundStyle(QRTheme.radar)
                    .symbolEffect(.pulse, options: .repeating, isActive: page == 0)

                Text("QuantRadar")
                    .font(.system(size: 36, weight: .bold, design: .rounded))
                    .foregroundStyle(QRTheme.text)

                TabView(selection: $page) {
                    ForEach(pages.indices, id: \.self) { i in
                        VStack(spacing: 10) {
                            Text(pages[i].title)
                                .font(.title3.weight(.semibold))
                                .foregroundStyle(QRTheme.text)
                                .multilineTextAlignment(.center)
                            Text(pages[i].body)
                                .font(.body)
                                .foregroundStyle(QRTheme.muted)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 28)
                        }
                        .tag(i)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .always))
                .frame(height: 160)

                Button {
                    if page < pages.count - 1 {
                        withAnimation { page += 1 }
                    } else {
                        hasSeenOnboarding = true
                    }
                } label: {
                    Text(page < pages.count - 1 ? "Continue" : "Open radar")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(QRTheme.radar)
                        .foregroundStyle(Color.black)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
                .padding(.horizontal, 24)

                Text("Educational only — not investment advice.")
                    .font(.caption)
                    .foregroundStyle(QRTheme.muted)
                    .padding(.bottom, 24)
            }
        }
    }
}
