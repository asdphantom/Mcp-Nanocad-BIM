using System;
using System.Collections.Concurrent;
using System.Threading;
using System.Threading.Tasks;
using Timer = System.Windows.Forms.Timer;

namespace CadEngine
{
    /// <summary>
    /// Executes delegates on the main CAD thread via a polling timer.
    /// Required for MultiCAD API calls (McTable.PlaceObject, etc.) that
    /// cannot run on background threads even with LockDocument().
    /// 
    /// Note: nanoCAD's Application.Idle event does NOT fire reliably from
    /// background threads. Instead, we use a System.Windows.Forms.Timer
    /// that polls the queue every 100ms on the main thread.
    /// </summary>
    public static class MainThreadExecutor
    {
        private static readonly ConcurrentQueue<(Func<object?> Action, TaskCompletionSource<object?> Tcs)> _queue = new();
        private static Timer? _timer;
        private static readonly object _lock = new();
        private static int _processing;

        /// <summary>
        /// Start the polling timer on the main CAD thread.
        /// Called once during plugin startup from PluginEntry.Initialize().
        /// </summary>
        public static void Initialize()
        {
            if (_timer != null) return;
            lock (_lock)
            {
                if (_timer != null) return;
                _timer = new Timer();
                _timer.Tick += (s, e) => ProcessQueue();
                _timer.Interval = 100; // poll every 100ms
                _timer.Start();
                PluginEntry.DebugLog("MainThreadExecutor initialized via polling timer (100ms)");
            }
        }

        /// <summary>
        /// Queue a delegate to execute on the main CAD thread.
        /// Blocks the calling thread until completion, with a timeout.
        /// </summary>
        /// <param name="action">Delegate to execute on main thread.</param>
        /// <param name="timeoutMs">Timeout in milliseconds (default 30000).</param>
        /// <returns>The result of the delegate, or null on timeout; action errors are propagated.</returns>
        public static object? Execute(Func<object?> action, int timeoutMs = 30000)
        {
            var tcs = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously);
            _queue.Enqueue((action, tcs));

            // The UI timer drains the queue. A space is not a no-op in CAD:
            // it can repeat the last command or answer an interactive prompt.

            try
            {
                tcs.Task.Wait(timeoutMs);
                if (tcs.Task.IsCompletedSuccessfully)
                    return tcs.Task.Result;
                // A timed-out queued action must not mutate a later active document.
                tcs.TrySetCanceled();
                return null;
            }
            catch (AggregateException ex)
            {
                System.Runtime.ExceptionServices.ExceptionDispatchInfo.Capture(ex.GetBaseException()).Throw();
                throw;
            }
        }

        /// <summary>
        /// Async version — queue and await the result without blocking.
        /// </summary>
        public static Task<object?> ExecuteAsync(Func<object?> action, int timeoutMs = 30000)
        {
            var tcs = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously);
            _queue.Enqueue((action, tcs));
            // Let the UI timer drain the queue without sending command input.
            return AwaitResult(tcs, timeoutMs);
        }

        private static async Task<object?> AwaitResult(TaskCompletionSource<object?> tcs, int timeoutMs)
        {
            try { return await tcs.Task.WaitAsync(TimeSpan.FromMilliseconds(timeoutMs)).ConfigureAwait(false); }
            catch { tcs.TrySetCanceled(); throw; }
        }

        /// <summary>
        /// Process all queued items. Called by the polling timer on the main thread.
        /// Exceptions from actions are caught and returned to the waiting thread
        /// via the TaskCompletionSource.
        /// </summary>
        private static void ProcessQueue()
        {
            // Document.Open/modal CAD code can pump Windows messages, including another timer tick.
            // Do not execute another native operation inside an unfinished operation.
            if (Interlocked.Exchange(ref _processing, 1) != 0) return;
            try
            {
                while (_queue.TryDequeue(out var item))
                {
                    if (item.Tcs.Task.IsCompleted) continue;
                    try
                    {
                        CadContext.RefreshDocument();
                        var result = item.Action();
                        item.Tcs.TrySetResult(result);
                    }
                    catch (Exception ex)
                    {
                        PluginEntry.DebugLog($"Main thread action failed: {ex}");
                        item.Tcs.TrySetException(ex);
                    }
                }
            }
            finally { Volatile.Write(ref _processing, 0); }
        }
    }
}
