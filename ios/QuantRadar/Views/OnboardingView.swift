import SwiftUI

struct OnboardingView: View {
    @Binding var hasSeenOnboarding: Bool

    var body: some View {
        ZStack {
            QRTheme.bg.ignoresSafeArea()
            VStack(spacing: 28) {
                Spacer()
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
                    Text("Chase Check asks three questions, then the radar gives one mechanical posture. Most days the honest answer is wait.")
                        .font(.body)
                        .foregroundStyle(QRTheme.muted)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 28)
                    Text("Free includes today’s SPY plus one ticker of yours. Unlock once for the full radar.")
                        .font(.footnote.weight(.medium))
                        .foregroundStyle(QRTheme.text)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 28)
                    Text("No account. Your decision journal stays on this device.")
                        .font(.caption)
                        .foregroundStyle(QRTheme.radar)
                }

                Button {
                    hasSeenOnboarding = true
                } label: {
                    Text("Open radar")
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
            .frame(maxWidth: 620)
        }
    }
}
