import { useEffect, useRef, useSyncExternalStore } from 'react'
import { ConnectionController, type ConnectionOptions, type ConnectionState } from './connection'

/** React binding for the framework-free connection controller. */
export function useConnection(options: ConnectionOptions): {
  connection: ConnectionState
  check: (options?: { force?: boolean }) => Promise<ConnectionState>
} {
  const optionsRef = useRef(options)
  optionsRef.current = options
  const controllerRef = useRef<ConnectionController | null>(null)
  if (!controllerRef.current) {
    controllerRef.current = new ConnectionController({
      ...options,
      fetchStatus: signal => optionsRef.current.fetchStatus(signal),
    })
  }
  const controller = controllerRef.current
  useEffect(() => {
    controller.start()
    return () => controller.stop()
  }, [controller])
  const connection = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot)
  return { connection, check: controller.check }
}
