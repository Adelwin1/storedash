package com.storedash.relay;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.Locale;
import java.util.UUID;

final class RelayConfig {
    private static final String PREFS = "storedash_relay";

    private static final String BACKEND_URL = "backend_url";
    private static final String LEGACY_RELAY_KEY = "relay_key";
    private static final String ALLOWED_SENDERS = "allowed_senders";
    private static final String DEVICE_ID = "device_id";
    private static final String LAST_STATUS = "last_status";

    private RelayConfig() {}

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(
            PREFS,
            Context.MODE_PRIVATE
        );
    }

    static String backendUrl(Context context) {
        return prefs(context).getString(
            BACKEND_URL,
            ""
        );
    }

    static String relayKey(Context context) {
        String secured =
            SecretStore.loadRelayKey(context);

        if (!secured.isBlank()) {
            return secured;
        }

        String legacy =
            prefs(context).getString(
                LEGACY_RELAY_KEY,
                ""
            );

        if (
            legacy != null
            && !legacy.isBlank()
        ) {
            SecretStore.saveRelayKey(
                context,
                legacy
            );

            prefs(context)
                .edit()
                .remove(LEGACY_RELAY_KEY)
                .apply();

            return legacy;
        }

        return "";
    }

    static String allowedSenders(Context context) {
        return prefs(context).getString(
            ALLOWED_SENDERS,
            ""
        );
    }

    static String lastStatus(Context context) {
        return prefs(context).getString(
            LAST_STATUS,
            "No relay events yet."
        );
    }

    static String deviceId(Context context) {
        SharedPreferences preferences =
            prefs(context);

        String existing =
            preferences.getString(
                DEVICE_ID,
                ""
            );

        if (
            existing != null
            && !existing.isBlank()
        ) {
            return existing;
        }

        String created =
            UUID.randomUUID().toString();

        preferences
            .edit()
            .putString(
                DEVICE_ID,
                created
            )
            .apply();

        return created;
    }

    static void save(
        Context context,
        String backendUrl,
        String relayKey,
        String allowedSenders
    ) {
        prefs(context)
            .edit()
            .putString(
                BACKEND_URL,
                backendUrl.trim()
            )
            .putString(
                ALLOWED_SENDERS,
                allowedSenders.trim()
            )
            .remove(
                LEGACY_RELAY_KEY
            )
            .apply();

        SecretStore.saveRelayKey(
            context,
            relayKey.trim()
        );

        deviceId(context);
    }

    static boolean isConfigured(Context context) {
        return !backendUrl(context).isBlank()
            && !relayKey(context).isBlank()
            && !allowedSenders(context).isBlank();
    }

    static String endpoint(Context context) {
        String base =
            backendUrl(context).trim();

        while (base.endsWith("/")) {
            base = base.substring(
                0,
                base.length() - 1
            );
        }

        return base
            + "/api/payments/sms-relay/events";
    }

    static boolean isSenderAllowed(
        Context context,
        String sender
    ) {
        if (
            sender == null
            || sender.isBlank()
        ) {
            return false;
        }

        String wanted =
            canonicalSender(sender);

        String configured =
            allowedSenders(context);

        for (
            String candidate :
            configured.split("[,;\\n]")
        ) {
            if (
                canonicalSender(candidate)
                    .equals(wanted)
            ) {
                return true;
            }
        }

        return false;
    }

    static void recordStatus(
        Context context,
        String status
    ) {
        prefs(context)
            .edit()
            .putString(
                LAST_STATUS,
                status
            )
            .apply();
    }

    private static String canonicalSender(
        String value
    ) {
        return value
            .trim()
            .toLowerCase(Locale.ROOT)
            .replaceAll(
                "[\\s\\-()]",
                ""
            );
    }
}
