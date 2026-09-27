using System;
using System.Globalization;
using System.Linq;
using BIMStructureMgd.Common;
using BIMStructureMgd.DatabaseObjects;
using HostMgd.ApplicationServices;
using Teigha.DatabaseServices;
using App = HostMgd.ApplicationServices.Application;

namespace CadEngine.Services
{
    public static class BimAssociationService
    {
        private static bool TryHandle(string text, out Handle handle)
        {
            handle = default;
            if (string.IsNullOrWhiteSpace(text) ||
                !long.TryParse(text, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var value) ||
                value <= 0)
                return false;
            handle = new Handle(value);
            return true;
        }

        public static object Create(BimAssociationRequest request)
        {
            if (!TryHandle(request.MasterHandle, out var masterHandle) ||
                !TryHandle(request.SlaveHandle, out var slaveHandle) ||
                masterHandle.Value == slaveHandle.Value)
                return new { success = false, error = "Two distinct hexadecimal entity handles are required" };

            return MainThreadExecutor.Execute(() =>
            {
                var doc = App.DocumentManager.MdiActiveDocument;
                if (doc == null) return new { success = false, error = "No active nanoCAD document" };
                using var docLock = doc.LockDocument();
                var db = doc.Database;
                ObjectId masterId, slaveId;
                try
                {
                    masterId = db.GetObjectId(false, masterHandle, 0);
                    slaveId = db.GetObjectId(false, slaveHandle, 0);
                }
                catch (Exception)
                {
                    return new { success = false, error = "An association target handle was not found" };
                }
                using (var tr = db.TransactionManager.StartTransaction())
                {
                    if (tr.GetObject(masterId, OpenMode.ForRead) is not Entity ||
                        tr.GetObject(slaveId, OpenMode.ForRead) is not Entity)
                        return new { success = false, error = "Association targets must be drawing entities" };
                }
                // The SDK sample creates the association outside a caller transaction.
                var associationId = AssociationUtilities.CreateAssociation(masterId, slaveId);
                if (associationId.IsNull)
                    return new { success = false, error = "The BIM SDK did not create an association" };
                using var readTr = db.TransactionManager.StartTransaction();
                var association = readTr.GetObject(associationId, OpenMode.ForRead) as ObjectAssociation;
                return new
                {
                    success = association != null,
                    handle = association?.Handle.Value.ToString("X"),
                    entity_type = association?.GetType().Name,
                    internal_name = association?.InternalName,
                    master_handle = request.MasterHandle,
                    slave_handle = request.SlaveHandle
                };
            }) ?? new { success = false, error = "Timed out waiting for nanoCAD main thread" };
        }

        public static object List(string entityHandle)
        {
            if (!TryHandle(entityHandle, out var handle))
                return new { success = false, error = "A hexadecimal entity handle is required" };
            return MainThreadExecutor.Execute(() =>
            {
                var doc = App.DocumentManager.MdiActiveDocument;
                if (doc == null) return new { success = false, error = "No active nanoCAD document" };
                using var docLock = doc.LockDocument();
                var db = doc.Database;
                ObjectId entityId;
                try { entityId = db.GetObjectId(false, handle, 0); }
                catch (Exception) { return new { success = false, error = "Entity handle was not found" }; }
                using var tr = db.TransactionManager.StartTransaction();
                if (tr.GetObject(entityId, OpenMode.ForRead) is not Entity)
                    return new { success = false, error = "Handle is not a drawing entity" };
                var masterId = AssociationUtilities.GetMasterAssociation(entityId);
                var master = masterId.IsNull ? null : tr.GetObject(masterId, OpenMode.ForRead) as ObjectAssociation;
                var slaves = AssociationUtilities.GetSlaveAssociations(entityId)
                    .Select(id => tr.GetObject(id, OpenMode.ForRead) as ObjectAssociation)
                    .Where(a => a != null)
                    .Select(a => new { handle = a!.Handle.Value.ToString("X"), internal_name = a.InternalName })
                    .ToArray();
                return new
                {
                    success = true,
                    entity_handle = entityHandle,
                    master_association = master == null ? null : new { handle = master.Handle.Value.ToString("X"), internal_name = master.InternalName },
                    slave_associations = slaves
                };
            }) ?? new { success = false, error = "Timed out waiting for nanoCAD main thread" };
        }
    }
}
