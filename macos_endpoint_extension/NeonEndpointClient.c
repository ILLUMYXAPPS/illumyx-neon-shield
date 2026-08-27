/*
 * Neon Shield macOS Endpoint Security notification client.
 *
 * Observation-only scaffold for a macOS System Extension target.
 * It intentionally subscribes only to NOTIFY events and never authorizes,
 * blocks, modifies, or reads file contents. The host app should consume the
 * normalized events and pass only approved fields into Neon Forensics.
 *
 * Apple requires the com.apple.developer.endpoint-security.client entitlement
 * for Endpoint Security clients. See macos_endpoint_extension/README.md.
 */
#include <EndpointSecurity/EndpointSecurity.h>
#include <dispatch/dispatch.h>
#include <stdio.h>
#include <stdlib.h>

static void print_token(const es_string_token_t token) {
    if (token.data == NULL || token.length == 0) {
        return;
    }
    fwrite(token.data, 1, token.length, stdout);
}

static void handle_event(es_client_t *client, const es_message_t *message) {
    (void)client;
    if (message == NULL || message->process == NULL) {
        return;
    }

    const char *type = "unknown";
    switch (message->event_type) {
        case ES_EVENT_TYPE_NOTIFY_EXEC:
            type = "exec";
            break;
        case ES_EVENT_TYPE_NOTIFY_FORK:
            type = "fork";
            break;
        default:
            return;
    }

    printf("{\"event_type\":\"%s\",\"pid\":%d,\"parent_pid\":%d,\"executable\":\"",
           type,
           audit_token_to_pid(message->process->audit_token),
           message->process->ppid);
    print_token(message->process->executable->path);
    printf("\"}\n");
    fflush(stdout);
}

int main(void) {
    es_client_t *client = NULL;
    es_new_client_result_t result = es_new_client(&client, handle_event);
    if (result != ES_NEW_CLIENT_RESULT_SUCCESS || client == NULL) {
        fprintf(stderr, "Neon Endpoint Security client creation failed: %d\n", result);
        return EXIT_FAILURE;
    }

    es_event_type_t events[] = {
        ES_EVENT_TYPE_NOTIFY_EXEC,
        ES_EVENT_TYPE_NOTIFY_FORK,
    };

    es_return_t subscribe_result = es_subscribe(client, events, sizeof(events) / sizeof(events[0]));
    if (subscribe_result != ES_RETURN_SUCCESS) {
        fprintf(stderr, "Neon Endpoint Security subscription failed: %d\n", subscribe_result);
        es_delete_client(client);
        return EXIT_FAILURE;
    }

    dispatch_main();
    return EXIT_SUCCESS;
}
