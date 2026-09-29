//
//  OtrofestivApp.swift
//  Otrofestiv
//
//  Created by Juanda on 5/14/26.
//

import SwiftUI

extension Notification.Name {
    /// La Live Activity abre la app en Mi Plan (otrofestiv://plan).
    static let otfOpenPlan = Notification.Name("otfOpenPlan")
}

@main
struct OtrofestivApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .onOpenURL { url in
                    if url.scheme == "otrofestiv" && url.host == "plan" {
                        NotificationCenter.default.post(name: .otfOpenPlan, object: nil)
                    }
                }
        }
    }
}
