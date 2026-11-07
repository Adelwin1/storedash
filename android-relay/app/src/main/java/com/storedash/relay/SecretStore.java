package com.storedash.relay;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class SecretStore {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String ALIAS = "storedash_relay_key_v1";
    private static final String PREFS = "storedash_relay_secrets";
    private static final String CIPHERTEXT = "relay_key_ciphertext";
    private static final String IV = "relay_key_iv";

    private SecretStore() {}

    static void saveRelayKey(Context context, String relayKey) {
        try {
            SecretKey key = getOrCreateKey();

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, key);

            byte[] encrypted = cipher.doFinal(
                relayKey.getBytes(StandardCharsets.UTF_8)
            );

            SharedPreferences prefs = context.getSharedPreferences(
                PREFS,
                Context.MODE_PRIVATE
            );

            prefs.edit()
                .putString(
                    CIPHERTEXT,
                    Base64.encodeToString(encrypted, Base64.NO_WRAP)
                )
                .putString(
                    IV,
                    Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP)
                )
                .apply();

        } catch (Exception e) {
            throw new IllegalStateException(
                "Could not securely store relay key.",
                e
            );
        }
    }

    static String loadRelayKey(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(
            PREFS,
            Context.MODE_PRIVATE
        );

        String ciphertext = prefs.getString(CIPHERTEXT, "");
        String iv = prefs.getString(IV, "");

        if (
            ciphertext == null || ciphertext.isBlank()
            || iv == null || iv.isBlank()
        ) {
            return "";
        }

        try {
            SecretKey key = getOrCreateKey();

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");

            cipher.init(
                Cipher.DECRYPT_MODE,
                key,
                new GCMParameterSpec(
                    128,
                    Base64.decode(iv, Base64.NO_WRAP)
                )
            );

            byte[] plaintext = cipher.doFinal(
                Base64.decode(ciphertext, Base64.NO_WRAP)
            );

            return new String(
                plaintext,
                StandardCharsets.UTF_8
            );

        } catch (Exception e) {
            return "";
        }
    }

    private static SecretKey getOrCreateKey() throws Exception {
        KeyStore keyStore = KeyStore.getInstance(KEYSTORE);
        keyStore.load(null);

        if (keyStore.containsAlias(ALIAS)) {
            return (SecretKey) keyStore.getKey(ALIAS, null);
        }

        KeyGenerator generator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            KEYSTORE
        );

        generator.init(
            new KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_ENCRYPT
                    | KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(
                    KeyProperties.ENCRYPTION_PADDING_NONE
                )
                .build()
        );

        return generator.generateKey();
    }
}
