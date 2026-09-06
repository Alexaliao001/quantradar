import SwiftUI

struct OnboardingView: View {
    @Binding var hasSeenOnboarding: Bool

    var body: some View {
        ZStack {
            QRTheme.bg.ignoresSafeArea()
            ScrollView {
                VStack(spacing: 28) {
                    Image(systemName: "dot.radiowaves.left.and.right")
                        .font(.system(size: 56, weight: .light))
                        .foregroundStyle(QRTheme.radar)

                    Text("QuantRadar")
                        .font(.system(size: 36, weight: .bold, design: .rounded))
                        .foregroundStyle(QRTheme.text)

                    VStack(spacing: 10) {
                        Text("Before you chase, check your process.")
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(QRTheme.text)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 24)
                        Text("Write your reason, the condition you will wait for, and what would change your mind. Keep that original plan beside a dated review of what you actually did.")
                            .font(.body)
                            .foregroundStyle(QRTheme.muted)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 28)
                        Text("Your plan and review work offline, free. Market context includes SPY plus one ticker of yours; Unlock adds the full radar.")
                            .font(.footnote.weight(.medium))
                            .foregroundStyle(QRTheme.text)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 28)
                        Text("No account. Your decision journal stays on this device.")
                            .font(.caption)
                            .foregroundStyle(QRTheme.radar)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 24)
                    }

                    Button {
                        hasSeenOnboarding = true
                    } label: {
                        Text("Start my plan")
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
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                        .padding(.bottom, 24)
                }
                .frame(maxWidth: 620)
                .padding(.vertical, 24)
                .frame(maxWidth: .infinity)
            }
        }
    }
}
