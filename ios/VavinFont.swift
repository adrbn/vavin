//
//  VavinFont.swift
//  Aura
//
//  Typographic identity for Aura, built on Vavin (SIL OFL 1.1).
//
//  SETUP - three steps, and step 2 is the one everyone forgets:
//
//  1. Drag Vavin-Regular-Latin.ttf and Vavin-Bold-Latin.ttf into the
//     Xcode project. Tick "Copy items if needed" and your app target under
//     "Add to targets". Confirm afterwards in
//     Target > Build Phases > Copy Bundle Resources - if they are not listed
//     there, they are not in the app and nothing below will work.
//
//  2. In Info.plist add an array key `UIAppFonts` ("Fonts provided by
//     application") with one string per FILE NAME:
//
//         <key>UIAppFonts</key>
//         <array>
//             <string>Vavin-Regular-Latin.ttf</string>
//             <string>Vavin-Bold-Latin.ttf</string>
//         </array>
//
//  3. Call fonts by their POSTSCRIPT name, not the file name and not the
//     family name: "Vavin-Regular", "Vavin-Bold". Run
//     Vavin.debugDumpInstalledNames() once if in doubt - it prints exactly
//     what iOS registered.
//
//  Attribution: the OFL requires the licence to travel with the software.
//  Ship OFL.txt in the bundle and surface it in your acknowledgements screen;
//  Vavin.licenceNotice below is ready for that.
//

import SwiftUI

// MARK: - Font family

enum Vavin {

    static let regular = "Vavin-Regular"
    static let bold = "Vavin-Bold"

    /// Line height baked into the font, in ems.
    ///
    /// The font declares hhea.ascender 879 and hhea.descender -321 on a 1000
    /// unit em with a zero line gap, so
    /// `UIFont.lineHeight == (879 + 321) / 1000 == 1.20 em`.
    /// At 17 pt that is 20.4 pt. Identical in Regular and Bold - the two
    /// styles share one metric set on purpose, so emboldening a run of text
    /// cannot reflow the paragraph around it.
    static let lineHeightEm: CGFloat = 1.20

    /// Ratio of x-height to point size, measured from the built font
    /// (468 units on a 1000 unit em).
    ///
    /// Useful for optical alignment: to sit a Vavin cap-line flush with an
    /// SF Pro one, compare x-heights rather than point sizes.
    static let xHeightRatio: CGFloat = 0.468
}

// MARK: - SwiftUI

extension Font {

    /// Vavin at a fixed size. Prefer `vavin(_:_:relativeTo:)` in UI that
    /// should respond to Dynamic Type.
    static func vavin(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font {
        .custom(weight >= .semibold ? Vavin.bold : Vavin.regular, size: size)
    }

    /// Vavin scaled by Dynamic Type, relative to a system text style.
    ///
    /// This is the form you want almost everywhere. `Font.custom(_:size:)`
    /// alone returns a fixed size that ignores the user's text-size setting,
    /// which is an accessibility regression the moment you adopt a custom
    /// face.
    static func vavin(
        _ size: CGFloat,
        _ weight: Font.Weight = .regular,
        relativeTo style: Font.TextStyle
    ) -> Font {
        .custom(
            weight >= .semibold ? Vavin.bold : Vavin.regular,
            size: size,
            relativeTo: style
        )
    }
}

// MARK: - A small type scale

extension Font {
    static let auraDisplay = Font.vavin(34, .bold, relativeTo: .largeTitle)
    static let auraTitle = Font.vavin(26, .bold, relativeTo: .title)
    static let auraHeadline = Font.vavin(19, .semibold, relativeTo: .headline)
    static let auraBody = Font.vavin(17, .regular, relativeTo: .body)
    static let auraCallout = Font.vavin(15, .regular, relativeTo: .callout)
    static let auraCaption = Font.vavin(13, .regular, relativeTo: .caption)
}

// MARK: - Line spacing

extension View {

    /// Set leading as a multiple of the point size.
    ///
    /// SwiftUI's `.lineSpacing` is *extra* space between lines, not the total
    /// line height, so it has to be computed against what the font already
    /// contributes. Vavin's large x-height wants slightly more air than a
    /// classic Garamond at the same size: 1.35 to 1.45 reads well for body
    /// copy, against 1.25 to 1.30 for the original.
    func vavinLeading(_ multiple: CGFloat, size: CGFloat) -> some View {
        lineSpacing(max(0, size * (multiple - Vavin.lineHeightEm)))
    }
}

// MARK: - Diagnostics

extension Vavin {

    /// Print every registered family and its PostScript names.
    ///
    /// Call once from `.onAppear` while wiring things up. If "Vavin" is
    /// absent, the font is not in Copy Bundle Resources or not listed in
    /// UIAppFonts - those are the only two causes, in that order of
    /// likelihood.
    static func debugDumpInstalledNames() {
        #if canImport(UIKit)
        for family in UIFont.familyNames.sorted() where family.contains("Vavin") {
            print("family: \(family)")
            for name in UIFont.fontNames(forFamilyName: family) {
                print("   PostScript name: \(name)")
            }
        }
        if !UIFont.familyNames.contains(where: { $0.contains("Vavin") }) {
            print("""
            Vavin is NOT registered. In order of likelihood:
              1. the .ttf files are not in Build Phases > Copy Bundle Resources
              2. UIAppFonts in Info.plist does not list them by file name
              3. the file names in UIAppFonts do not match the files exactly
            """)
        }
        #endif
    }

    /// Attribution string for an acknowledgements screen. Shipping this, or
    /// OFL.txt itself, is a licence requirement rather than a courtesy.
    static let licenceNotice = """
        Vavin
        Copyright 2026 The Vavin Project Authors.
        Derived from EB Garamond, Copyright 2017 The EB Garamond Project \
        Authors.
        Licensed under the SIL Open Font License, Version 1.1.
        https://openfontlicense.org
        """
}

// MARK: - Preview

#Preview("Vavin type scale") {
    ScrollView {
        VStack(alignment: .leading, spacing: 18) {
            Text("Aura").font(.auraDisplay)
            Text("Écouter autrement").font(.auraTitle)
            Text("Nouveautés de la semaine").font(.auraHeadline)
            Text(
                "Il y a dans toute typographie de labeur une tension entre ce "
                + "qui se voit et ce qui se lit. La hauteur d'x décide de la "
                + "quantité d'encre que le lecteur rencontre à chaque mot."
            )
            .font(.auraBody)
            .vavinLeading(1.40, size: 17)

            Divider()
            ForEach([9, 11, 13, 15, 17, 22, 28], id: \.self) { size in
                Text("Portez ce vieux whisky au juge blond — \(size) pt")
                    .font(.vavin(CGFloat(size)))
            }
        }
        .padding(24)
    }
    .onAppear { Vavin.debugDumpInstalledNames() }
}
