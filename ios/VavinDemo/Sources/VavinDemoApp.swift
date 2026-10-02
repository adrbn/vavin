//
//  VavinDemoApp.swift
//
//  A throwaway harness whose only job is to prove Vavin actually registers
//  and renders on iOS. The three things that can go wrong when embedding a
//  font are all visible here:
//
//    * the file is not in Copy Bundle Resources  -> the family is absent
//    * UIAppFonts does not list it               -> the family is absent
//    * the PostScript name is wrong              -> silent fallback to system
//
//  The last one is the dangerous one, because the app still looks fine. The
//  "REGISTRATION" panel below therefore reads back what iOS actually loaded
//  rather than trusting that the call succeeded.
//

import SwiftUI
import UIKit

// MARK: - Registration check

struct Registration {
    let familyFound: Bool
    let postScriptNames: [String]
    let regularResolves: Bool
    let boldResolves: Bool
    let lineHeight17: CGFloat
    let capHeightRatio: CGFloat
    let xHeightRatio: CGFloat

    static func probe() -> Registration {
        let family = UIFont.familyNames.first { $0.contains("Vavin") }
        let names = family.map { UIFont.fontNames(forFamilyName: $0) } ?? []
        let regular = UIFont(name: "Vavin-Regular", size: 17)
        let bold = UIFont(name: "Vavin-Bold", size: 17)
        return Registration(
            familyFound: family != nil,
            postScriptNames: names.sorted(),
            regularResolves: regular != nil,
            boldResolves: bold != nil,
            lineHeight17: regular?.lineHeight ?? 0,
            capHeightRatio: (regular?.capHeight ?? 0) / 17.0,
            xHeightRatio: (regular?.xHeight ?? 0) / 17.0
        )
    }
}

// MARK: - App

@main
struct VavinDemoApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}

struct ContentView: View {
    private let reg = Registration.probe()

    private let sample = "Le vaisseau glisse sur l'eau noire, et la ville "
        + "s'endort derrière lui."

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                registrationPanel
                Divider()
                scale
                Divider()
                comparison
                Divider()
                accents
            }
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("Vavin")
                .font(.custom("Vavin-Regular", size: 56))
            Text("v0.1 · SIL OFL 1.1 · derived from EB Garamond")
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(.secondary)
        }
    }

    private var registrationPanel: some View {
        VStack(alignment: .leading, spacing: 5) {
            row("family registered", reg.familyFound)
            row("Vavin-Regular resolves", reg.regularResolves)
            row("Vavin-Bold resolves", reg.boldResolves)
            ForEach(reg.postScriptNames, id: \.self) { name in
                Text("   \(name)")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
            Text(String(
                format: "   lineHeight @17pt  %.2f pt  (%.3f em)",
                reg.lineHeight17, reg.lineHeight17 / 17.0
            ))
            .font(.system(size: 11, design: .monospaced))
            .foregroundStyle(.secondary)
            Text(String(
                format: "   x-height %.3f em   cap-height %.3f em   ratio %.3f",
                reg.xHeightRatio, reg.capHeightRatio,
                reg.xHeightRatio / max(reg.capHeightRatio, 0.0001)
            ))
            .font(.system(size: 11, design: .monospaced))
            .foregroundStyle(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.secondary.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
    }

    private func row(_ label: String, _ ok: Bool) -> some View {
        HStack(spacing: 6) {
            Image(systemName: ok ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundStyle(ok ? .green : .red)
            Text(label).font(.system(size: 12, design: .monospaced))
        }
    }

    private var scale: some View {
        VStack(alignment: .leading, spacing: 10) {
            label("TYPE SCALE")
            Text("Écouter autrement").font(.custom("Vavin-Bold", size: 30))
            Text("Nouveautés de la semaine")
                .font(.custom("Vavin-Bold", size: 20))
            Text(sample)
                .font(.custom("Vavin-Regular", size: 17, relativeTo: .body))
                .lineSpacing(17 * (1.40 - 1.20))
            Text(sample).font(.custom("Vavin-Regular", size: 13))
        }
    }

    private var comparison: some View {
        VStack(alignment: .leading, spacing: 10) {
            label("AGAINST THE SYSTEM FONT, SAME POINT SIZE")
            Text(sample).font(.system(size: 15))
            Text(sample).font(.custom("Vavin-Regular", size: 15))
            Text("The large x-height is why the second line looks bigger "
                 + "at an identical 15 pt.")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
        }
    }

    private var accents: some View {
        VStack(alignment: .leading, spacing: 10) {
            label("DIACRITICS — precomposed and decomposed")
            Text("éèêë áàâäã íìîï óòôöõ úùûü ñ ç ÉÀÊÔ")
                .font(.custom("Vavin-Regular", size: 24))
            // Combining marks: exercises the GPOS mark anchors instead of the
            // precomposed glyphs, which is a different code path entirely.
            Text("e\u{0301} a\u{0300} o\u{0302} u\u{0308} n\u{0303} c\u{0327}")
                .font(.custom("Vavin-Regular", size: 24))
            Text("0123456789 €$£ &@#% .,;:!? «» \u{201C}\u{201D} — –")
                .font(.custom("Vavin-Regular", size: 20))
        }
    }

    private func label(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 10, weight: .semibold, design: .monospaced))
            .foregroundStyle(.tint)
    }
}
