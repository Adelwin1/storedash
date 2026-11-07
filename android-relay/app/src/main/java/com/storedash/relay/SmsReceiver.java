package com.storedash.relay;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.provider.Telephony;
import android.telephony.SmsMessage;

import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.concurrent.TimeUnit;

public final class SmsReceiver extends BroadcastReceiver {

    private static final int MAX_BODY_CHARS = 6000;

    @Override
    public void onReceive(
        Context context,
        Intent intent
    ) {
        if (
            !Telephony.Sms.Intents.SMS_RECEIVED_ACTION
                .equals(intent.getAction())
        ) {
            return;
        }

        SmsMessage[] messages =
            Telephony.Sms.Intents
                .getMessagesFromIntent(intent);

        if (
            messages == null
            || messages.length == 0
        ) {
            RelayConfig.recordStatus(
                context,
                "SMS ignored: message payload was empty."
            );
            return;
        }

        String sender =
            messages[0].getOriginatingAddress();

        if (
            sender == null
            || sender.isBlank()
        ) {
            RelayConfig.recordStatus(
                context,
                "SMS ignored: sender was missing."
            );
            return;
        }

        StringBuilder body =
            new StringBuilder();

        long timestamp =
            messages[0].getTimestampMillis();

        for (SmsMessage message : messages) {
            String part =
                message.getMessageBody();

            if (part != null) {
                body.append(part);
            }
        }

        String bodyText =
            body.toString();

        if (bodyText.isBlank()) {
            RelayConfig.recordStatus(
                context,
                "SMS ignored: message body was empty."
            );
            return;
        }

        if (
            bodyText.length()
            > MAX_BODY_CHARS
        ) {
            RelayConfig.recordStatus(
                context,
                "SMS ignored: message exceeded relay size limit."
            );
            return;
        }

        if (!RelayConfig.isConfigured(context)) {
            RelayConfig.recordStatus(
                context,
                "SMS ignored: relay is not configured."
            );
            return;
        }

        if (
            !RelayConfig.isSenderAllowed(
                context,
                sender
            )
        ) {
            RelayConfig.recordStatus(
                context,
                "SMS ignored: sender is not allowlisted."
            );
            return;
        }

        String receivedAt =
            isoUtc(timestamp);

        Data input =
            new Data.Builder()
                .putString(
                    RelayWorker.SENDER,
                    sender
                )
                .putString(
                    RelayWorker.BODY,
                    bodyText
                )
                .putString(
                    RelayWorker.RECEIVED_AT,
                    receivedAt
                )
                .putString(
                    RelayWorker.DEVICE_ID,
                    RelayConfig.deviceId(
                        context
                    )
                )
                .build();

        Constraints constraints =
            new Constraints.Builder()
                .setRequiredNetworkType(
                    NetworkType.CONNECTED
                )
                .build();

        OneTimeWorkRequest work =
            new OneTimeWorkRequest.Builder(
                RelayWorker.class
            )
                .setInputData(input)
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    30,
                    TimeUnit.SECONDS
                )
                .build();

        String uniqueName =
            "storedash-sms-"
                + sha256(
                    sender
                    + "|"
                    + bodyText
                    + "|"
                    + receivedAt
                );

        WorkManager
            .getInstance(context)
            .enqueueUniqueWork(
                uniqueName,
                ExistingWorkPolicy.KEEP,
                work
            );

        RelayConfig.recordStatus(
            context,
            "Payment SMS queued for StoreDash."
        );
    }

    private static String isoUtc(
        long millis
    ) {
        SimpleDateFormat format =
            new SimpleDateFormat(
                "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",
                Locale.US
            );

        format.setTimeZone(
            TimeZone.getTimeZone("UTC")
        );

        return format.format(
            new Date(millis)
        );
    }

    private static String sha256(
        String value
    ) {
        try {
            MessageDigest digest =
                MessageDigest.getInstance(
                    "SHA-256"
                );

            byte[] hash =
                digest.digest(
                    value.getBytes(
                        StandardCharsets.UTF_8
                    )
                );

            StringBuilder result =
                new StringBuilder();

            for (byte item : hash) {
                result.append(
                    String.format(
                        Locale.ROOT,
                        "%02x",
                        item
                    )
                );
            }

            return result.toString();

        } catch (Exception exception) {
            return Integer.toHexString(
                value.hashCode()
            );
        }
    }
}
