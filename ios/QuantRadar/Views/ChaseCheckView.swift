import SwiftUI

struct ChaseCheckView: View {
    @Binding var check: ChaseCheck
    let ticker: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Chase Check")
                        .font(.headline)
                        .foregroundStyle(QRTheme.text)
                    Text(ticker.isEmpty ? "Interrupt urgency before the score." : "Before reading \(ticker), check your process.")
                        .font(.caption)
                        .foregroundStyle(QRTheme.muted)
                }
                Spacer()
                Text(check.status)
                    .font(.caption2.monospaced().weight(.bold))
                    .foregroundStyle(check.isClear ? QRTheme.radar : QRTheme.warn)
            }

            checkRow(
                "My entry existed before this move",
                systemImage: "scope",
                isOn: $check.entryWasPlanned
            )
            checkRow(
                "I can name what invalidates the setup",
                systemImage: "xmark.diamond",
                isOn: $check.invalidationIsDefined
            )
            checkRow(
                "I would consider it without social hype",
                systemImage: "person.2.slash",
                isOn: $check.independentOfHype
            )

            Text(check.guidance)
                .font(.caption)
                .foregroundStyle(check.isClear ? QRTheme.radar : QRTheme.muted)
        }
        .padding(14)
        .background(QRTheme.panel)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Chase Check, \(check.completedCount) of 3 process checks complete")
    }

    private func checkRow(
        _ title: String,
        systemImage: String,
        isOn: Binding<Bool>
    ) -> some View {
        Button {
            isOn.wrappedValue.toggle()
        } label: {
            HStack(spacing: 10) {
                Image(systemName: isOn.wrappedValue ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isOn.wrappedValue ? QRTheme.radar : QRTheme.muted)
                Image(systemName: systemImage)
                    .foregroundStyle(QRTheme.muted)
                    .frame(width: 18)
                Text(title)
                    .font(.subheadline)
                    .foregroundStyle(QRTheme.text)
                Spacer()
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityValue(isOn.wrappedValue ? "Checked" : "Not checked")
    }
}

struct DecisionCommitView: View {
    let verdict: RadarVerdict
    let chaseCheck: ChaseCheck
    let isSaved: Bool
    let onSave: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Your decision")
                .font(.headline)
                .foregroundStyle(QRTheme.text)

            Text(decisionExplanation)
                .font(.footnote)
                .foregroundStyle(QRTheme.muted)

            if isSaved {
                Label("Saved privately on this device", systemImage: "checkmark.seal.fill")
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(QRTheme.radar)
            } else {
                Button(action: onSave) {
                    Label(buttonTitle, systemImage: "checkmark.shield")
                        .font(.subheadline.weight(.semibold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(chaseCheck.isClear ? QRTheme.radar : QRTheme.warn)
                .foregroundStyle(.black)
            }
        }
        .padding(14)
        .background(QRTheme.panel)
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private var buttonTitle: String {
        if !chaseCheck.isClear { return "Log: pause" }
        switch verdict.actionCode {
        case "NO", "AVOID": return "Log: pass"
        case "WAIT": return "Log: wait"
        default: return "Log: review, don’t chase"
        }
    }

    private var decisionExplanation: String {
        if !chaseCheck.isClear {
            return "The mechanical score stays unchanged. Your personal process gate says pause."
        }
        return "Record the decision before the outcome. Grade the process later, not the next candle."
    }
}
