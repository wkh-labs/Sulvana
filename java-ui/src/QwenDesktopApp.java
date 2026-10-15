import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import javafx.application.Application;
import javafx.application.Platform;
import javafx.geometry.Insets;
import javafx.geometry.NodeOrientation;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.Button;
import javafx.scene.control.ComboBox;
import javafx.scene.control.Label;
import javafx.scene.control.ScrollPane;
import javafx.scene.control.Slider;
import javafx.scene.control.Spinner;
import javafx.scene.control.TextArea;
import javafx.scene.input.Clipboard;
import javafx.scene.input.ClipboardContent;
import javafx.scene.input.KeyCode;
import javafx.scene.image.Image;
import javafx.scene.image.ImageView;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.Priority;
import javafx.scene.layout.Region;
import javafx.scene.layout.StackPane;
import javafx.scene.layout.VBox;
import javafx.stage.Stage;
import javafx.stage.FileChooser;

public final class QwenDesktopApp extends Application {
    private static final String WORKSPACE = "/home/tanchjim/Documents/Codex/ai-workspace";
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    private final ExecutorService io = Executors.newCachedThreadPool(task -> {
        Thread thread = new Thread(task, "qwen-io");
        thread.setDaemon(true);
        return thread;
    });
    private final ScheduledExecutorService polling = Executors.newSingleThreadScheduledExecutor(task -> {
        Thread thread = new Thread(task, "qwen-status");
        thread.setDaemon(true);
        return thread;
    });

    private volatile URI endpoint;
    private volatile String token;
    private volatile Process backend;
    private volatile boolean closing;
    private boolean ready;
    private boolean busy;
    private boolean hasMessages;
    private boolean scrollPinned = true;

    private Label statusText;
    private Label statusDot;
    private Label modelDetail;
    private Label metrics;
    private Label emptyState;
    private TextArea composer;
    private Button sendButton;
    private Button stopButton;
    private Button newChatButton;
    private Button attachImageButton;
    private ComboBox<String> language;
    private Spinner<Integer> maxTokens;
    private Slider temperature;
    private Label temperatureValue;
    private VBox chatList;
    private ScrollPane chatScroll;
    private Path attachedImage;

    private static String decode(String value) {
        return new String(Base64.getDecoder().decode(value), StandardCharsets.UTF_8);
    }

    private static String encode(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private static Label label(String text, String styleClass) {
        Label result = new Label(text);
        result.getStyleClass().add(styleClass);
        return result;
    }

    private static Button button(String text, String styleClass) {
        Button result = new Button(text);
        result.getStyleClass().add(styleClass);
        result.setFocusTraversable(false);
        return result;
    }

    @Override
    public void start(Stage stage) {
        BorderPane root = new BorderPane();
        root.getStyleClass().add("app-root");
        root.setLeft(buildSidebar());
        root.setCenter(buildMain());
        Scene scene = new Scene(root, 1140, 780);
        scene.getStylesheets().add(URI.create("file:" + WORKSPACE + "/java-ui/chat.css").toString());
        stage.setScene(scene);
        stage.setTitle("Sulvana");
        stage.setMinWidth(790);
        stage.setMinHeight(620);
        stage.show();
        updateControls();
        startBackend();
    }

    private VBox buildSidebar() {
        Label mark = label("✦", "brand-mark");
        Label brand = label("Sulvana", "brand-title");
        Label caption = label("Your private AI workspace", "brand-caption");
        VBox brandCopy = new VBox(3, brand, caption);
        HBox brandRow = new HBox(12, mark, brandCopy);
        brandRow.setAlignment(Pos.CENTER_LEFT);

        newChatButton = button("＋  New chat", "new-chat-button");
        newChatButton.setMaxWidth(Double.MAX_VALUE);
        newChatButton.setOnAction(event -> clearChat());

        Label modelHeading = label("MODEL", "section-heading");
        Label modelName = label("Dolphin 3.0 · 8B", "model-name");
        modelDetail = label("Starting local backend…", "model-detail");
        modelDetail.setWrapText(true);
        VBox modelCard = new VBox(6, modelName, modelDetail);
        modelCard.getStyleClass().add("sidebar-card");

        Label languageHeading = label("REPLY LANGUAGE", "section-heading");
        language = new ComboBox<>();
        language.getItems().addAll(
            "Auto (match my message)", "English", "ខ្មែរ (Khmer)", "中文 (Chinese)",
            "Español", "العربية", "हिन्दी", "Français", "日本語", "한국어",
            "Português", "Deutsch", "Русский", "ไทย", "Tiếng Việt"
        );
        language.setEditable(true);
        language.setValue("Auto (match my message)");
        language.setMaxWidth(Double.MAX_VALUE);
        language.getStyleClass().add("language-picker");
        Label languageHint = label("Type any language in the field above.", "hint");
        languageHint.setWrapText(true);

        Label settingsHeading = label("GENERATION", "section-heading");
        maxTokens = new Spinner<>(64, 1024, 256, 64);
        maxTokens.setEditable(true);
        maxTokens.setMaxWidth(Double.MAX_VALUE);
        maxTokens.getStyleClass().add("token-spinner");
        Label tokensLabel = label("Max reply tokens", "setting-label");
        temperature = new Slider(0.2, 1.2, 0.7);
        temperature.setBlockIncrement(0.1);
        temperature.setMaxWidth(Double.MAX_VALUE);
        temperatureValue = label("0.7", "setting-value");
        temperature.valueProperty().addListener((observable, oldValue, newValue) ->
            temperatureValue.setText(String.format(Locale.ROOT, "%.1f", newValue.doubleValue()))
        );
        HBox temperatureHeader = new HBox(label("Creativity", "setting-label"), new Region(), temperatureValue);
        HBox.setHgrow(temperatureHeader.getChildren().get(1), Priority.ALWAYS);

        Region spacer = new Region();
        VBox.setVgrow(spacer, Priority.ALWAYS);
        Label privacy = label("●  Runs on this laptop", "privacy-label");
        Label caution = label("Language quality depends on the model. Check important answers.", "hint");
        caution.setWrapText(true);

        VBox side = new VBox(17,
            brandRow, newChatButton, modelHeading, modelCard,
            languageHeading, language, languageHint,
            settingsHeading, tokensLabel, maxTokens, temperatureHeader, temperature,
            spacer, privacy, caution
        );
        side.getStyleClass().add("sidebar");
        side.setPrefWidth(270);
        side.setMinWidth(245);
        side.setMaxWidth(290);
        return side;
    }

    private VBox buildMain() {
        Label heading = label("Chat", "chat-heading");
        Label subheading = label("Ask anything in your language", "chat-subheading");
        VBox headingCopy = new VBox(3, heading, subheading);
        statusDot = label("●", "status-dot");
        statusText = label("Starting…", "status-text");
        HBox status = new HBox(7, statusDot, statusText);
        status.setAlignment(Pos.CENTER_RIGHT);
        Region headerGap = new Region();
        HBox.setHgrow(headerGap, Priority.ALWAYS);
        HBox header = new HBox(20, headingCopy, headerGap, status);
        header.getStyleClass().add("main-header");
        header.setAlignment(Pos.CENTER_LEFT);

        emptyState = label("✦\n\nYour conversation starts here.\nAsk a question in any language.", "empty-state");
        emptyState.setTextAlignment(javafx.scene.text.TextAlignment.CENTER);
        emptyState.setAlignment(Pos.CENTER);
        emptyState.setMaxWidth(Double.MAX_VALUE);

        chatList = new VBox(20, emptyState);
        chatList.getStyleClass().add("chat-list");
        chatList.setFillWidth(true);
        chatScroll = new ScrollPane(chatList);
        chatScroll.getStyleClass().add("chat-scroll");
        chatScroll.setFitToWidth(true);
        chatScroll.setHbarPolicy(ScrollPane.ScrollBarPolicy.NEVER);
        chatScroll.vvalueProperty().addListener((observable, oldValue, newValue) ->
            scrollPinned = newValue.doubleValue() > 0.92
        );
        VBox.setVgrow(chatScroll, Priority.ALWAYS);

        composer = new TextArea();
        composer.setPromptText("Message Sulvana…");
        composer.setWrapText(true);
        composer.setPrefRowCount(3);
        composer.getStyleClass().add("composer-input");
        composer.setOnKeyPressed(event -> {
            if (event.getCode() == KeyCode.ENTER && !event.isShiftDown() && !event.isControlDown()) {
                sendMessage();
                event.consume();
            }
        });
        VBox.setVgrow(composer, Priority.ALWAYS);
        sendButton = button("Send  ↗", "send-button");
        sendButton.setOnAction(event -> sendMessage());
        stopButton = button("Stop", "stop-button");
        stopButton.setOnAction(event -> stopGeneration());
        attachImageButton = button("＋ Image", "attach-image-button");
        attachImageButton.setOnAction(event -> chooseImage());
        Region actionGap = new Region();
        HBox.setHgrow(actionGap, Priority.ALWAYS);
        HBox actions = new HBox(9, attachImageButton, actionGap, stopButton, sendButton);
        actions.setAlignment(Pos.BOTTOM_RIGHT);
        VBox composerBox = new VBox(12, composer, actions);
        composerBox.getStyleClass().add("composer-box");

        Label shortcut = label("Enter to send  ·  Shift+Enter for a new line", "footer-hint");
        metrics = label("Local · Offline", "footer-hint");
        Region footerGap = new Region();
        HBox.setHgrow(footerGap, Priority.ALWAYS);
        HBox footer = new HBox(10, shortcut, footerGap, metrics);
        footer.setAlignment(Pos.CENTER_LEFT);
        footer.getStyleClass().add("footer");

        VBox bottom = new VBox(0, composerBox, footer);
        VBox main = new VBox(header, chatScroll, bottom);
        main.getStyleClass().add("main-panel");
        VBox.setVgrow(chatScroll, Priority.ALWAYS);
        return main;
    }

    private void setStatus(String message, boolean warning) {
        statusText.setText(message);
        statusDot.getStyleClass().removeAll("status-ready", "status-warning");
        statusDot.getStyleClass().add(warning ? "status-warning" : "status-ready");
    }

    private void updateControls() {
        sendButton.setDisable(!ready || busy);
        stopButton.setDisable(!busy);
        newChatButton.setDisable(!ready || busy);
        composer.setDisable(!ready || busy);
        attachImageButton.setDisable(!ready || busy);
    }

    private void startBackend() {
        io.execute(() -> {
            try {
                ProcessBuilder builder = new ProcessBuilder(
                    WORKSPACE + "/run-performance.sh", "python", "-u", WORKSPACE + "/qwen_server.py"
                );
                builder.redirectErrorStream(true);
                backend = builder.start();
                try (BufferedReader lines = new BufferedReader(
                    new InputStreamReader(backend.getInputStream(), StandardCharsets.UTF_8)
                )) {
                    String line;
                    boolean connected = false;
                    String lastStartupLine = "The local backend exited. Restart the app to try again.";
                    while ((line = lines.readLine()) != null) {
                        if (line.startsWith("QWEN_SERVER_READY\t")) {
                            String[] parts = line.split("\t", 3);
                            endpoint = URI.create("http://127.0.0.1:" + parts[1]);
                            token = parts[2];
                            connected = true;
                            Platform.runLater(() -> setStatus("Loading model…", false));
                            polling.scheduleAtFixedRate(this::refreshStatus, 0, 500, TimeUnit.MILLISECONDS);
                        } else if (!line.isBlank() && !connected) {
                            String detail = line;
                            lastStartupLine = detail;
                            Platform.runLater(() -> modelDetail.setText(detail));
                        }
                    }
                    if (!closing) {
                        String failure = connected
                            ? "The local backend exited. Restart the app to try again."
                            : lastStartupLine;
                        Platform.runLater(() -> backendFailed(failure));
                    }
                }
            } catch (Exception error) {
                if (!closing) {
                    Platform.runLater(() -> backendFailed("Could not start Python backend: " + error.getMessage()));
                }
            }
        });
    }

    private HttpRequest.Builder request(String path) {
        return HttpRequest.newBuilder(endpoint.resolve(path))
            .timeout(Duration.ofMinutes(5))
            .header("X-Local-Token", token);
    }

    private void refreshStatus() {
        if (closing || endpoint == null) return;
        try {
            HttpRequest req = request("/status").timeout(Duration.ofSeconds(3)).GET().build();
            HttpResponse<String> response = http.send(req, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (response.statusCode() != 200) return;
            String[] parts = response.body().strip().split("\t", 2);
            if (parts.length != 2) return;
            String state = parts[0];
            String detail = decode(parts[1]);
            Platform.runLater(() -> {
                if (closing) return;
                modelDetail.setText(detail);
                if (state.equals("fatal")) {
                    backendFailed(detail);
                } else if (state.equals("ready")) {
                    ready = true;
                    if (!busy) setStatus("Ready", false);
                    updateControls();
                } else if (state.equals("loading")) {
                    setStatus("Loading model…", false);
                }
            });
        } catch (Exception ignored) {
            // The backend may still be starting or shutting down.
        }
    }

    private void backendFailed(String message) {
        ready = false;
        busy = false;
        setStatus("Unavailable", true);
        modelDetail.setText(message);
        updateControls();
    }

    private String chosenLanguage() {
        String value = language.getEditor().getText().trim();
        return value.equals("Auto (match my message)") ? "Auto" : value;
    }

    private void sendMessage() {
        if (!ready || busy) return;
        String prompt = composer.getText().strip();
        Path image = attachedImage;
        if (prompt.isEmpty() && image == null) return;
        int requestedTokens;
        try {
            maxTokens.commitValue();
            requestedTokens = maxTokens.getValue();
        } catch (Exception error) {
            setStatus("Enter a valid token limit", true);
            return;
        }
        String replyLanguage = chosenLanguage();
        double creativity = temperature.getValue();
        if (image != null && prompt.isEmpty()) prompt = "Describe this image in detail.";
        String displayPrompt = image == null ? prompt : "📎 " + image.getFileName() + "\n" + prompt;
        composer.clear();
        attachedImage = null;
        attachImageButton.setText("＋ Image");
        addMessage("You", displayPrompt, true);
        MessageCard answer = addMessage("Sulvana", "", false);
        busy = true;
        setStatus(image == null ? "Generating…" : "Analyzing image…", false);
        metrics.setText(image == null ? "Working…" : "Vision model loading…");
        updateControls();
        String submittedPrompt = prompt;
        if (image == null) {
            io.execute(() -> streamReply(submittedPrompt, answer, requestedTokens, creativity, replyLanguage));
        } else {
            io.execute(() -> streamVision(submittedPrompt, image, answer));
        }
    }

    private void chooseImage() {
        if (attachedImage != null) {
            attachedImage = null;
            attachImageButton.setText("＋ Image");
            metrics.setText("Local · Offline");
            composer.setPromptText("Message Sulvana…");
            return;
        }
        FileChooser chooser = new FileChooser();
        chooser.setTitle("Choose an image for Sulvana to analyze");
        chooser.getExtensionFilters().add(new FileChooser.ExtensionFilter(
            "Images", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"
        ));
        File selected = chooser.showOpenDialog(composer.getScene().getWindow());
        if (selected == null) return;
        attachedImage = selected.toPath().toAbsolutePath().normalize();
        attachImageButton.setText("Remove image");
        composer.setPromptText("Ask about the attached image…");
        metrics.setText("Image attached · " + attachedImage.getFileName());
        composer.requestFocus();
    }

    private void streamReply(String prompt, MessageCard answer, int requestedTokens,
                             double creativity, String replyLanguage) {
        try {
            HttpRequest req = request("/chat")
                .header("Content-Type", "text/plain; charset=utf-8")
                .header("X-Max-Tokens", Integer.toString(requestedTokens))
                .header("X-Temperature", String.format(Locale.ROOT, "%.2f", creativity))
                .header("X-Language", encode(replyLanguage))
                .POST(HttpRequest.BodyPublishers.ofString(prompt, StandardCharsets.UTF_8))
                .build();
            HttpResponse<java.io.InputStream> response = http.send(req, HttpResponse.BodyHandlers.ofInputStream());
            if (response.statusCode() != 200) {
                try (java.io.InputStream input = response.body()) {
                    throw new IOException("Backend returned " + response.statusCode() + ": "
                        + new String(input.readAllBytes(), StandardCharsets.UTF_8));
                }
            }
            try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(response.body(), StandardCharsets.US_ASCII)
            )) {
                String line;
                while ((line = reader.readLine()) != null) {
                    String[] parts = line.split("\t", 2);
                    if (parts.length != 2) continue;
                    String value = decode(parts[1]);
                    if (parts[0].equals("t")) {
                        Platform.runLater(() -> {
                            answer.append(value);
                            if (scrollPinned) scrollToBottom();
                        });
                    } else if (parts[0].equals("d")) {
                        String stats = value;
                        Platform.runLater(() -> finishReply(stats));
                        return;
                    } else if (parts[0].equals("i")) {
                        boolean complete = handleImageEvent(value, answer);
                        if (complete) return;
                    } else if (parts[0].equals("v")) {
                        boolean complete = handleVisionEvent(value, answer);
                        if (complete) return;
                    } else if (parts[0].equals("e")) {
                        throw new IOException(value);
                    }
                }
            }
            throw new IOException("The model stream ended before the reply finished.");
        } catch (Exception error) {
            String message = error.getMessage() == null ? error.toString() : error.getMessage();
            Platform.runLater(() -> {
                answer.append("\n[Generation failed: " + message + "]");
                busy = false;
                setStatus("Generation failed", true);
                metrics.setText("Local · Offline");
                updateControls();
            });
        }
    }

    private void streamVision(String prompt, Path image, MessageCard answer) {
        try {
            HttpRequest req = request("/vision")
                .header("Content-Type", "text/plain; charset=utf-8")
                .header("X-Image-Path", encode(image.toString()))
                .POST(HttpRequest.BodyPublishers.ofString(prompt, StandardCharsets.UTF_8))
                .build();
            HttpResponse<java.io.InputStream> response = http.send(req, HttpResponse.BodyHandlers.ofInputStream());
            if (response.statusCode() != 200) {
                try (java.io.InputStream input = response.body()) {
                    throw new IOException("Backend returned " + response.statusCode() + ": "
                        + new String(input.readAllBytes(), StandardCharsets.UTF_8));
                }
            }
            try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(response.body(), StandardCharsets.US_ASCII)
            )) {
                String line;
                while ((line = reader.readLine()) != null) {
                    String[] parts = line.split("\\t", 2);
                    if (parts.length != 2) continue;
                    String value = decode(parts[1]);
                    if (parts[0].equals("v")) {
                        if (handleVisionEvent(value, answer)) return;
                    } else if (parts[0].equals("e")) {
                        throw new IOException(value);
                    }
                }
            }
            throw new IOException("The vision stream ended before analysis finished.");
        } catch (Exception error) {
            String message = error.getMessage() == null ? error.toString() : error.getMessage();
            Platform.runLater(() -> {
                answer.setText("[Image analysis failed: " + message + "]");
                busy = false;
                setStatus("Image analysis failed", true);
                metrics.setText("Local · Offline");
                updateControls();
            });
        }
    }

    private void finishReply(String stats) {
        busy = false;
        boolean stopped = stats.contains("\"stopped\": true");
        boolean loop = stats.contains("\"loop_guard_triggered\": true");
        if (loop) setStatus("Repetition loop stopped", true);
        else if (stopped) setStatus("Stopped", true);
        else setStatus("Ready", false);
        String tokens = extractNumber(stats, "output_tokens");
        String speed = extractNumber(stats, "tokens_per_second");
        String vram = extractNumber(stats, "peak_vram_gib");
        try {
            metrics.setText(tokens + " tokens  ·  "
                + String.format(Locale.ROOT, "%.1f", Double.parseDouble(speed)) + " tok/s  ·  "
                + String.format(Locale.ROOT, "%.2f", Double.parseDouble(vram)) + " GiB VRAM");
        } catch (NumberFormatException error) {
            metrics.setText("Reply complete");
        }
        updateControls();
        composer.requestFocus();
    }

    private boolean handleImageEvent(String event, MessageCard answer) {
        String state = extractJsonString(event, "state");
        if (state.equals("started")) {
            Platform.runLater(() -> {
                answer.setText("Preparing Z-Image Turbo…\nDolphin is temporarily freeing GPU memory.");
                setStatus("Generating image…", false);
                metrics.setText("Rendering locally…");
                if (scrollPinned) scrollToBottom();
            });
            return false;
        }
        if (state.equals("done")) {
            String imagePath = extractJsonString(event, "image_path");
            String elapsed = extractNumber(event, "elapsed_seconds");
            Platform.runLater(() -> {
                try {
                    answer.showImage(Path.of(imagePath), elapsed);
                    metrics.setText("Image complete  ·  " + elapsed + " s  ·  Local");
                    setStatus("Ready", false);
                } catch (Exception error) {
                    answer.setText("Image was generated, but the preview could not be displayed.\n" + imagePath);
                    metrics.setText("Image complete");
                    setStatus("Ready", false);
                }
                busy = false;
                updateControls();
                composer.requestFocus();
                if (scrollPinned) scrollToBottom();
            });
            return true;
        }
        return false;
    }

    private boolean handleVisionEvent(String event, MessageCard answer) {
        String state = extractJsonString(event, "state");
        if (state.equals("started")) {
            Platform.runLater(() -> {
                answer.setText("Loading Sulvana Vision…\nDolphin is temporarily freeing GPU memory.");
                setStatus("Analyzing image…", false);
                metrics.setText("Understanding image locally…");
            });
            return false;
        }
        if (state.equals("done")) {
            String response = extractJsonString(event, "answer");
            String elapsed = extractNumber(event, "elapsed_seconds");
            Platform.runLater(() -> {
                answer.setText(response);
                busy = false;
                setStatus("Ready", false);
                metrics.setText("Image understood  ·  " + elapsed + " s  ·  Local");
                updateControls();
                composer.requestFocus();
                if (scrollPinned) scrollToBottom();
            });
            return true;
        }
        return false;
    }

    private static String extractNumber(String json, String name) {
        java.util.regex.Matcher match = java.util.regex.Pattern
            .compile("\\\"" + name + "\\\"\\s*:\\s*([0-9.]+)").matcher(json);
        return match.find() ? match.group(1) : "0";
    }

    private static String extractJsonString(String json, String name) {
        java.util.regex.Matcher match = java.util.regex.Pattern.compile(
            "\\\"" + java.util.regex.Pattern.quote(name) + "\\\"\\s*:\\s*\\\"((?:\\\\.|[^\\\"])*)\\\""
        ).matcher(json);
        if (!match.find()) return "";
        return match.group(1)
            .replace("\\/", "/")
            .replace("\\\\", "\\")
            .replace("\\\"", "\"");
    }

    private void stopGeneration() {
        if (!busy || endpoint == null) return;
        setStatus("Stopping…", true);
        io.execute(() -> simplePost("/stop"));
    }

    private void clearChat() {
        if (!ready || busy || endpoint == null) return;
        io.execute(() -> {
            if (simplePost("/clear")) {
                Platform.runLater(() -> {
                    chatList.getChildren().clear();
                    chatList.getChildren().add(emptyState);
                    hasMessages = false;
                    metrics.setText("Local · Offline");
                    setStatus("New chat ready", false);
                    composer.requestFocus();
                });
            }
        });
    }

    private boolean simplePost(String path) {
        try {
            HttpRequest req = request(path)
                .timeout(Duration.ofSeconds(path.equals("/shutdown") ? 4 : 10))
                .POST(HttpRequest.BodyPublishers.noBody()).build();
            return http.send(req, HttpResponse.BodyHandlers.discarding()).statusCode() == 204;
        } catch (Exception ignored) {
            return false;
        }
    }

    private MessageCard addMessage(String speaker, String content, boolean user) {
        if (!hasMessages) {
            chatList.getChildren().remove(emptyState);
            hasMessages = true;
        }
        MessageCard card = new MessageCard(speaker, content, user);
        chatList.getChildren().add(card.row);
        scrollToBottom();
        return card;
    }

    private void scrollToBottom() {
        Platform.runLater(() -> chatScroll.setVvalue(1.0));
    }

    private static NodeOrientation textOrientation(String text) {
        for (int offset = 0; offset < text.length();) {
            int codepoint = text.codePointAt(offset);
            byte direction = Character.getDirectionality(codepoint);
            if (direction == Character.DIRECTIONALITY_RIGHT_TO_LEFT
                || direction == Character.DIRECTIONALITY_RIGHT_TO_LEFT_ARABIC) {
                return NodeOrientation.RIGHT_TO_LEFT;
            }
            if (direction == Character.DIRECTIONALITY_LEFT_TO_RIGHT) {
                return NodeOrientation.LEFT_TO_RIGHT;
            }
            offset += Character.charCount(codepoint);
        }
        return NodeOrientation.LEFT_TO_RIGHT;
    }

    private final class MessageCard {
        final HBox row;
        final Label body;
        final VBox bubble;
        ImageView imageView;

        MessageCard(String speaker, String content, boolean user) {
            Label name = label(speaker, user ? "user-name" : "assistant-name");
            body = label(content.isEmpty() ? "Thinking…" : content, "message-body");
            body.setWrapText(true);
            body.setMaxWidth(700);
            body.setNodeOrientation(textOrientation(content));
            Button copy = button("Copy", "copy-button");
            copy.setOnAction(event -> {
                ClipboardContent data = new ClipboardContent();
                data.putString(body.getText());
                Clipboard.getSystemClipboard().setContent(data);
                copy.setText("Copied");
                javafx.animation.PauseTransition delay = new javafx.animation.PauseTransition(
                    javafx.util.Duration.seconds(1.5)
                );
                delay.setOnFinished(done -> copy.setText("Copy"));
                delay.play();
            });
            Region gap = new Region();
            HBox.setHgrow(gap, Priority.ALWAYS);
            HBox top = new HBox(10, name, gap, copy);
            top.setAlignment(Pos.CENTER_LEFT);
            bubble = new VBox(9, top, body);
            bubble.getStyleClass().add(user ? "user-bubble" : "assistant-bubble");
            bubble.setMaxWidth(760);
            row = new HBox(bubble);
            row.getStyleClass().add("message-row");
            row.setAlignment(user ? Pos.CENTER_RIGHT : Pos.CENTER_LEFT);
            row.setPadding(new Insets(0, 30, 0, 30));
        }

        void append(String piece) {
            String old = body.getText();
            String next = old.equals("Thinking…") ? piece : old + piece;
            body.setText(next);
            body.setNodeOrientation(textOrientation(next));
        }

        void setText(String text) {
            body.setText(text);
            body.setNodeOrientation(textOrientation(text));
        }

        void showImage(Path path, String elapsed) {
            setText("Image ready · " + elapsed + " seconds");
            if (imageView != null) bubble.getChildren().remove(imageView);
            Image image = new Image(path.toUri().toString(), 660, 0, true, true, true);
            imageView = new ImageView(image);
            imageView.getStyleClass().add("generated-image");
            imageView.setPreserveRatio(true);
            imageView.setFitWidth(660);
            Button open = button("Open image", "image-open-button");
            open.setOnAction(event -> getHostServices().showDocument(path.toUri().toString()));
            HBox imageActions = new HBox(open);
            imageActions.getStyleClass().add("image-actions");
            bubble.getChildren().addAll(imageView, imageActions);
        }
    }

    @Override
    public void stop() {
        closing = true;
        polling.shutdownNow();
        if (endpoint != null) {
            simplePost("/shutdown");
        }
        Process process = backend;
        if (process != null && process.isAlive()) {
            try {
                if (!process.waitFor(3, TimeUnit.SECONDS)) process.destroy();
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt();
                process.destroy();
            }
        }
        io.shutdownNow();
    }

    public static void main(String[] args) {
        launch(args);
    }
}
