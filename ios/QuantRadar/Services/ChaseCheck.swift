import Foundation

/// A user-owned process check. It never changes the mechanical market score.
/// Its job is to interrupt urgency before the user interprets a setup.
struct ChaseCheck: Equatable {
    var entryWasPlanned = false
    var invalidationIsDefined = false
    var independentOfHype = false

    var completedCount: Int {
        [entryWasPlanned, invalidationIsDefined, independentOfHype]
            .filter { $0 }
            .count
    }

    var isClear: Bool {
        completedCount == 3
    }

    var status: String {
        isClear ? "PROCESS CLEAR" : "PAUSE"
    }

    var guidance: String {
        if isClear {
            return "Your entry, invalidation, and reason existed before the urge. Now read the radar."
        }
        return "An incomplete process is a reason to slow down — never a reason to chase."
    }

    mutating func reset() {
        entryWasPlanned = false
        invalidationIsDefined = false
        independentOfHype = false
    }
}
