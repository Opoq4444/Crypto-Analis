-keep class com.globalinsight.** { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
