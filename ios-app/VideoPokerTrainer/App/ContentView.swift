import SwiftUI
import UIKit

struct UiCard: Identifiable {
    let id = UUID()
    let suit: Int
    let rank: Int
    var held: Bool
    var winning: Bool = false
}

struct ContentView: View {
    @State private var engine: String = "solver"
    @State private var bet: Int = 5
    @State private var mlModelPath: String = ""
    @State private var initialCards: [UiCard] = []
    @State private var finalCards: [UiCard] = []
    @State private var payout: Int = 0
    @State private var errorText: String = ""
    @State private var suggestedMask: Int = 0
    @State private var canDraw: Bool = false
    @State private var autoHoldEnabled: Bool = true

    private let bridge = PokerEngineBridge(seed: UInt64(Date().timeIntervalSince1970 * 1000))

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                Text("Video Poker Trainer")
                    .font(.largeTitle.weight(.bold))
                    .multilineTextAlignment(.center)

                Picker("Engine", selection: $engine) {
                    Text("solver").tag("solver")
                    Text("rule").tag("rule")
                    Text("ml").tag("ml")
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 400)

                HStack(spacing: 20) {
                    HStack {
                        Text("Bet: \(bet)")
                            .font(.headline)
                        Stepper("", value: $bet, in: 1...5)
                            .labelsHidden()
                    }
                    
                    Divider().frame(height: 24)
                    
                    HStack {
                        Toggle("Autohold", isOn: $autoHoldEnabled)
                            .labelsHidden()
                        Text("Autohold")
                            .font(.body)
                    }
                }

                if engine == "ml" {
                    TextField("ML model path (model.json)", text: $mlModelPath)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 300)
                }

                HStack(spacing: 16) {
                    Button("Deal Hand") {
                        dealSuggested()
                    }
                    .buttonStyle(.borderedProminent)

                    Button("Draw Selected") {
                        drawSelected()
                    }
                    .buttonStyle(.bordered)
                    .disabled(!canDraw)
                }

                if !errorText.isEmpty {
                    Text(errorText)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)
                }

                VStack(spacing: 20) {
                    VStack(spacing: 8) {
                        Text("Initial (tap to toggle holds)")
                            .font(.subheadline.weight(.semibold))
                        CardRow(
                            cards: initialCards, 
                            interactive: canDraw, 
                            suggestedMask: autoHoldEnabled ? suggestedMask : nil
                        ) { idx in
                            if canDraw {
                                initialCards[idx].held.toggle()
                            }
                        }
                    }
                    
                    VStack(spacing: 8) {
                        Text("Final")
                            .font(.subheadline.weight(.semibold))
                        CardRow(cards: finalCards, interactive: false, suggestedMask: nil) { _ in }
                    }
                }

                Text("Payout: \(payout)")
                    .font(.title.weight(.bold))
                    .foregroundColor(payout > 0 ? .green : .secondary)

                Spacer()
            }
            .padding()
            .frame(maxWidth: .infinity)
        }
    }

    private func prepareEngine() -> NSError? {
        do {
            try bridge.setEngine(engine)
            if engine == "ml" {
                if mlModelPath.isEmpty {
                    return NSError(domain: "PokerEngine", code: 3, userInfo: [NSLocalizedDescriptionKey: "Please provide ML model path"])
                }
                try bridge.loadMlModel(mlModelPath)
            }
            return nil
        } catch {
            return error as NSError
        }
    }

    private func dealSuggested() {
        errorText = ""
        if let err = prepareEngine() {
            errorText = err.localizedDescription
            return
        }

        let handData: [AnyHashable: Any]
        do {
            handData = try bridge.dealSuggested(withBet: bet)
        } catch {
            errorText = (error as NSError).localizedDescription
            return
        }

        payout = 0
        canDraw = true
        suggestedMask = handData["holdMask"] as? Int ?? 0

        let initial = handData["initial"] as? [[String: Any]] ?? []
        initialCards = initial.map {
            UiCard(
                suit: $0["s"] as? Int ?? 1,
                rank: $0["r"] as? Int ?? 2,
                held: autoHoldEnabled ? (($0["held"] as? Int ?? 0) == 1) : false,
                winning: ($0["winning"] as? Int ?? 0) == 1
            )
        }
        finalCards = []
    }

    private func drawSelected() {
        errorText = ""
        let mask = initialCards.enumerated().reduce(0) { acc, pair in
            let (idx, card) = pair
            return card.held ? (acc | (1 << idx)) : acc
        }

        let handData: [AnyHashable: Any]
        do {
            handData = try bridge.draw(withBet: bet, holdMask: UInt(mask))
        } catch {
            errorText = (error as NSError).localizedDescription
            return
        }

        canDraw = false
        payout = handData["payout"] as? Int ?? 0

        let initial = handData["initial"] as? [[String: Any]] ?? []
        initialCards = initial.map {
            UiCard(
                suit: $0["s"] as? Int ?? 1,
                rank: $0["r"] as? Int ?? 2,
                held: ($0["held"] as? Int ?? 0) == 1,
                winning: ($0["winning"] as? Int ?? 0) == 1
            )
        }

        let final = handData["final"] as? [[String: Any]] ?? []
        finalCards = final.map {
            UiCard(
                suit: $0["s"] as? Int ?? 1,
                rank: $0["r"] as? Int ?? 2,
                held: ($0["held"] as? Int ?? 0) == 1,
                winning: ($0["winning"] as? Int ?? 0) == 1
            )
        }
    }
}

struct CardRow: View {
    let cards: [UiCard]
    let interactive: Bool
    let suggestedMask: Int?
    let onTap: (Int) -> Void

    var body: some View {
        HStack(spacing: 8) {
            ForEach(Array(cards.enumerated()), id: \.element.id) { idx, card in
                ZStack {
                    cardImage(suit: card.suit, rank: card.rank)
                        .background(card.winning ? Color.yellow.opacity(0.1) : Color.white)
                        .cornerRadius(8)
                        .shadow(radius: 1)

                    if card.held && !card.winning {
                        Color.black.opacity(0.15)
                            .cornerRadius(8)
                        
                        VStack {
                            Spacer()
                            Text("HELD")
                                .font(.system(size: 8, weight: .heavy))
                                .foregroundColor(.white)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.orange)
                                .cornerRadius(2)
                        }
                        .padding(.bottom, 4)
                    }

                    if card.winning {
                        VStack {
                            Spacer()
                            Text("WIN")
                                .font(.system(size: 8, weight: .heavy))
                                .foregroundColor(.black)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.yellow)
                                .cornerRadius(2)
                        }
                        .padding(.bottom, 4)
                    }
                }
                .frame(width: 60, height: 90)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(strokeColor(index: idx, card: card), lineWidth: strokeWidth(index: idx, card: card))
                )
                .onTapGesture {
                    if interactive {
                        onTap(idx)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .center)
    }

    private func cardImageName(suit: Int, rank: Int) -> String {
        let r: String
        switch rank {
        case 14: r = "ace"
        case 13: r = "king"
        case 12: r = "queen"
        case 11: r = "jack"
        case 10: r = "ten"
        case 9: r = "nine"
        case 8: r = "eight"
        case 7: r = "seven"
        case 6: r = "six"
        case 5: r = "five"
        case 4: r = "four"
        case 3: r = "three"
        case 2: r = "two"
        default: r = ""
        }
        let s: String
        switch suit {
        case 1: s = "spades"
        case 2: s = "clubs"
        case 3: s = "hearts"
        case 4: s = "diamonds"
        default: s = ""
        }
        return "\(r)_\(s)"
    }

    private func cardImage(suit: Int, rank: Int) -> some View {
        let imageName = cardImageName(suit: suit, rank: rank)
        let uiImage = UIImage(
            contentsOfFile: Bundle.main.path(forResource: imageName, ofType: "png", inDirectory: "cards") ?? ""
        ) ?? UIImage(
            contentsOfFile: Bundle.main.path(forResource: "card_back", ofType: "png", inDirectory: "cards") ?? ""
        ) ?? UIImage()

        return Image(uiImage: uiImage)
            .resizable()
            .aspectRatio(contentMode: .fit)
    }

    private func strokeColor(index: Int, card: UiCard) -> Color {
        if card.winning { return .yellow }
        guard interactive, let suggestedMask else {
            return card.held ? .orange : Color.black.opacity(0.2)
        }
        let suggested = (suggestedMask & (1 << index)) != 0
        if card.held == suggested {
            return card.held ? .green : Color.black.opacity(0.2)
        }
        return .red
    }

    private func strokeWidth(index: Int, card: UiCard) -> CGFloat {
        if card.winning { return 3 }
        guard interactive, let suggestedMask else {
            return card.held ? 2 : 1
        }
        let suggested = (suggestedMask & (1 << index)) != 0
        return card.held == suggested ? (card.held ? 2 : 1) : 3
    }
}
