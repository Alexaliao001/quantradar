import SwiftUI

/// Blurred real verdict + anxiety copy. Score is computed; details stay locked.
struct LockedVerdictView: View {
    @EnvironmentObject private var purchases: PurchaseStore
    let verdict: RadarVerdict
    let onUnlock: () -> Void

    var body: some View {
        ZStack {
            VerdictCardView(verdict: verdict, showsShare: false)
                .blur(radius: 10)
                .allowsHitTesting(false)

            VStack(spacing: 12) {
                Text(AppAccess.anxietyCopy(ticker: verdict.ticker))
                    .font(.headline)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(QRTheme.text)
                Text("Posture is scored. Unlock to see it — one time, not a subscription.")
                    .font(.footnote)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(QRTheme.muted)
                Button(action: onUnlock) {
                    Text("Unlock to see · \(unlockPrice)")
                        .font(.subheadline.weight(.semibold))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 10)
                        .background(QRTheme.radar)
                        .foregroundStyle(.black)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
            }
            .padding(20)
        }
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private var unlockPrice: String {
        purchases.unlockProduct?.displayPrice ?? "$9.99"
    }
}
