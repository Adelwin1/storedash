package com.storedash.relay;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public final class RelayWorker extends Worker {

    static final String SENDER = "sender";
    static final String BODY = "body";
    static final String RECEIVED_AT = "received_at";
    static final String DEVICE_ID = "device_id";

    public RelayWorker(
        @NonNull Context context,
        @NonNull WorkerParameters params
    ) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Context context = getApplicationContext();

        if (!RelayConfig.isConfigured(context)) {
            RelayConfig.recordStatus(
                context,
                "Relay failed: configuration missing."
            );

            return Result.failure();
        }

        String sender = getInputData().getString(SENDER);
        String body = getInputData().getString(BODY);
        String receivedAt = getInputData().getString(RECEIVED_AT);
        String deviceId = getInputData().getString(DEVICE_ID);

        if (
            sender == null
            || body == null
            || receivedAt == null
        ) {
            RelayConfig.recordStatus(
                context,
                "Relay failed: queued SMS data is invalid."
            );

            return Result.failure();
        }

        HttpURLConnection connection = null;

        try {
            URL url =
                new URL(
                    RelayConfig.endpoint(context)
                );

            connection =
                (HttpURLConnection)
                    url.openConnection();

            connection.setRequestMethod("POST");
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(15000);
            connection.setDoOutput(true);

            connection.setRequestProperty(
                "Content-Type",
                "application/json"
            );

            connection.setRequestProperty(
                "Accept",
                "application/json"
            );

            connection.setRequestProperty(
                "X-StoreDash-Relay-Key",
                RelayConfig.relayKey(context)
            );

            connection.setRequestProperty(
                "User-Agent",
                "StoreDash-Relay/0.1"
            );

            JSONObject payload =
                new JSONObject();

            payload.put("sender", sender);
            payload.put("body", body);
            payload.put(
                "received_at",
                receivedAt
            );
            payload.put(
                "device_id",
                deviceId
            );

            byte[] bytes =
                payload
                    .toString()
                    .getBytes(
                        StandardCharsets.UTF_8
                    );

            connection.setFixedLengthStreamingMode(
                bytes.length
            );

            try (
                OutputStream output =
                    connection.getOutputStream()
            ) {
                output.write(bytes);
            }

            int status =
                connection.getResponseCode();

            if (
                status >= 200
                && status < 300
            ) {
                RelayConfig.recordStatus(
                    context,
                    "Last relay succeeded: HTTP "
                        + status
                );

                return Result.success();
            }

            if (
                status == 408
                || status == 429
                || status >= 500
            ) {
                RelayConfig.recordStatus(
                    context,
                    "Temporary server failure. Retrying: HTTP "
                        + status
                );

                return Result.retry();
            }

            if (
                status == 401
                || status == 403
            ) {
                RelayConfig.recordStatus(
                    context,
                    "Relay authentication failed: HTTP "
                        + status
                );

                return Result.failure();
            }

            if (
                status >= 400
                && status < 500
            ) {
                RelayConfig.recordStatus(
                    context,
                    "Relay rejected permanently: HTTP "
                        + status
                );

                return Result.failure();
            }

            RelayConfig.recordStatus(
                context,
                "Unexpected server response. Retrying: HTTP "
                    + status
            );

            return Result.retry();

        } catch (Exception exception) {
            RelayConfig.recordStatus(
                context,
                "Network failure. Relay will retry."
            );

            return Result.retry();

        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }
}
